import re

class ParameterTransformer:
    def __init__(self, mappings: dict):
        self.mappings = mappings
        self.unconvertible_expressions = []
        # Dictionary of common Make.com functions and their n8n equivalents
        self.function_mappings = {
            "parseDate": "new Date",
            "formatDate": "$items[0].json.date ? $items[0].json.date.toISOString() : ''",
            "toString": "String",
            "toNumber": "Number",
            "sum": "reduce((accumulator, currentValue) => accumulator + currentValue, 0)",
            "substring": "substring",
            "replace": "replace",
            "length": "length",
            "lower": "toLowerCase",
            "upper": "toUpperCase",
            "trim": "trim",
            "split": "split",
            "join": "join"
        }

    def transform_parameters(self, make_module: dict, n8n_node_type: str):
        """
        Transforms Make.com module parameters into n8n node parameters based on mappings.
        Handles nested parameters and expression conversion.
        """
        n8n_parameters = {}
        module_type = make_module.get("module")
        module_mapping = self.mappings.get(module_type, {})
        parameter_map = module_mapping.get("parameters", {})

        make_parameters = make_module.get("parameters", {})
        make_mapper = make_module.get("mapper", {})

        # Combine parameters from 'parameters' and 'mapper' fields in Make.com
        all_make_params = {**make_parameters, **make_mapper}

        for make_param_key, n8n_param_path in parameter_map.items():
            if make_param_key in all_make_params:
                make_value = all_make_params[make_param_key]
                converted_value = self._convert_expression(make_value)
                self._set_nested_value(n8n_parameters, n8n_param_path, converted_value)
            elif make_param_key == "routes" and "routes" in make_module: # Special handling for BasicRouter routes
                n8n_parameters["rules"] = {"values": []}
                for route in make_module["routes"]:
                    # For switch node, each route is a rule
                    # Make.com route has a 'flow' which contains the first node of the route
                    # n8n switch node has 'conditions' for each rule
                    rule = {
                        "outputKey": f"output_{len(n8n_parameters['rules']['values'])}",
                        "conditions": {
                            "conditions": []
                        }
                    }
                    
                    # Try to extract conditions from route if available
                    if "condition" in route:
                        condition = route["condition"]
                        if isinstance(condition, dict) and "operand1" in condition and "operand2" in condition and "operator" in condition:
                            op1 = self._convert_expression(condition["operand1"])
                            op2 = self._convert_expression(condition["operand2"])
                            operator = self._map_operator(condition["operator"])
                            
                            rule["conditions"]["conditions"].append({
                                "id": f"condition_{len(rule['conditions']['conditions'])}",
                                "value1": op1,
                                "operation": operator,
                                "value2": op2
                            })
                    
                    n8n_parameters["rules"]["values"].append(rule)
        
        # Add operation if specified in mapping
        if "operation" in module_mapping:
            n8n_parameters["operation"] = module_mapping["operation"]

        return n8n_parameters

    def _convert_expression(self, value):
        """
        Converts Make.com expressions (e.g., {{...}}) to n8n expressions (e.g., ={{...}}).
        Handles various Make.com expression patterns and functions.
        """
        if not isinstance(value, str):
            return value

        # Regex to find Make.com expressions: {{...}}
        make_expression_pattern = r"\{\{(.*?)\}\}"
        
        # Check if the entire value is an expression
        full_match = re.match(r"^\{\{(.*)\}\}$", value)
        if full_match:
            expression_content = full_match.group(1).strip()
            return self._transform_make_expression(expression_content, is_full_value=True)
            
        # Find all expressions
        matches = re.findall(make_expression_pattern, value)

        if not matches:
            return value # No expression found, return as is

        converted_parts = []
        last_idx = 0
        for match in re.finditer(make_expression_pattern, value):
            start, end = match.span()
            expression_content = match.group(1).strip()

            # Add the text before the current expression
            converted_parts.append(value[last_idx:start])

            # Convert the expression
            converted_expression = self._transform_make_expression(expression_content, is_full_value=False)
            converted_parts.append(converted_expression)
            
            last_idx = end
        
        # Add any remaining text after the last expression
        converted_parts.append(value[last_idx:])

        return "".join(converted_parts)

    def _transform_make_expression(self, expression_content, is_full_value=False):
        """
        Transforms a Make.com expression into an n8n expression.
        """
        # Direct item access (e.g., 1.data or $json.data)
        if re.match(r'\d+\..*', expression_content) or re.match(r'\$\w+\..*', expression_content):
            # For full value expressions, wrap in =
            if is_full_value:
                return f"={{ {expression_content} }}"
            return f"{{ {expression_content} }}"
        
        # Handle Make.com functions
        for make_func, n8n_func in self.function_mappings.items():
            # Pattern to match function calls: functionName(arguments)
            pattern = rf'{make_func}\((.*?)\)'
            if re.search(pattern, expression_content):
                try:
                    # Replace the function name and keep arguments
                    expression_content = re.sub(pattern, f'{n8n_func}(\\1)', expression_content)
                except Exception as e:
                    self.unconvertible_expressions.append(f"Error converting function {make_func}: {str(e)}")
        
        # Handle array references like myArray[0]
        if re.search(r'\[\d+\]', expression_content):
            # Already compatible with n8n
            if is_full_value:
                return f"={{ {expression_content} }}"
            return f"{{ {expression_content} }}"
        
        # Handle simple variable references (e.g., $data)
        if expression_content.startswith("$"):
            if is_full_value:
                return f"={{ {expression_content} }}"
            return f"{{ {expression_content} }}"
            
        # For other cases, mark as potentially unconvertible
        self.unconvertible_expressions.append(f"Potentially unconvertible expression: {{{{{expression_content}}}}}")
        return f"/* REVIEW_EXPRESSION: {{{{{expression_content}}}}} */"

    def _map_operator(self, make_operator):
        """
        Maps Make.com operators to n8n operators.
        """
        operator_map = {
            "equal": "equal",
            "notEqual": "notEqual",
            "greaterThan": "larger",
            "greaterThanOrEqual": "largerEqual",
            "lessThan": "smaller",
            "lessThanOrEqual": "smallerEqual",
            "contains": "contains",
            "notContains": "notContains",
            "startsWith": "startsWith",
            "notStartsWith": "notStartsWith",
            "endsWith": "endsWith",
            "notEndsWith": "notEndsWith",
            "isEmpty": "empty",
            "notEmpty": "notEmpty",
            "in": "in",
            "notIn": "notIn",
            "regex": "regex"
        }
        
        return operator_map.get(make_operator, "unknown")

    def _set_nested_value(self, obj, path, value):
        """
        Sets a value in a nested dictionary/list structure given a dot-separated path.
        Handles list indices (e.g., 'assignments[0].value').
        """
        parts = path.split('.')
        current = obj
        for i, part in enumerate(parts):
            # Check if we're dealing with array notation like 'values.string[0].name'
            if '[' in part and ']' in part:
                # Handle list index
                base_key, index_part = part.split('[', 1)
                index = int(index_part.split(']')[0])
                
                # Create the key if it doesn't exist
                if base_key not in current:
                    current[base_key] = {}
                
                # If the next path component is after ], we're accessing a property of the array element
                if '].' in part:
                    # Extract the property name after ]
                    prop = part.split('].')[1]
                    
                    # Make sure we have an array
                    if not isinstance(current[base_key], list):
                        current[base_key] = []
                    
                    # Ensure the array is long enough
                    while len(current[base_key]) <= index:
                        current[base_key].append({})
                    
                    if i == len(parts) - 1:
                        # If it's the last part, set the value
                        current[base_key][index][prop] = value
                    else:
                        # Otherwise continue traversing
                        current = current[base_key][index][prop]
                else:
                    # We're setting a direct array index
                    if not isinstance(current[base_key], list):
                        current[base_key] = []
                    
                    # Ensure the array is long enough
                    while len(current[base_key]) <= index:
                        current[base_key].append({})
                    
                    if i == len(parts) - 1:
                        current[base_key][index] = value
                    else:
                        current = current[base_key][index]
            else:
                # Handle dictionary key
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]