const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

function createHandler(appPath, options = {}) {
  const {
    app = 'app',
    env = {},
    debug = false,
  } = options;

  const appModule = path.basename(appPath, '.py');
  const appFile = path.resolve(appPath);

  return (event, context, callback) => {
    const server = http.createServer((req, res) => {
      const python = spawn(
        'python',
        [
          '-u',
          '-c',
          `from ${appModule} import ${app}; import aws_wsgi; aws_wsgi.CGIHandler(${app}).__call__(__import__('sys').stdin, __import__('sys').stdout, __import__('sys').stderr)`,
        ],
        {
          stdio: ['pipe', 'pipe', 'pipe'],
          env: {
            ...process.env,
            ...env,
          },
        }
      );

      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (debug) {
          console.log(`Python process exited with code ${code}`);
          console.log('stdout:', stdout);
          console.log('stderr:', stderr);
        }

        if (code !== 0) {
          return callback(new Error(stderr));
        }

        const lines = stdout.split('\r\n');
        const statusLine = lines.shift();
        const headers = {};
        let body = '';

        for (const line of lines) {
          if (line.trim() === '') {
            body = lines.slice(lines.indexOf(line) + 1).join('\r\n');
            break;
          }
          const [key, value] = line.split(': ');
          headers[key] = value;
        }

        const [_, statusCode] = statusLine.split(' ');
        res.statusCode = parseInt(statusCode, 10);
        for (const key in headers) {
          res.setHeader(key, headers[key]);
        }
        res.end(body);
      });

      const {
        httpMethod,
        path: eventPath,
        queryStringParameters,
        headers,
        body,
        isBase64Encoded,
      } = event;

      const query = new URLSearchParams(queryStringParameters).toString();
      const fullPath = query ? `${eventPath}?${query}` : eventPath;

      const requestLine = `${httpMethod} ${fullPath} HTTP/1.1\r\n`;
      const headerLines = Object.entries(headers)
        .map(([key, value]) => `${key}: ${value}\r\n`)
        .join('');
      const bodyContent = isBase64Encoded ? Buffer.from(body, 'base64').toString() : body;

      const requestData = `${requestLine}${headerLines}\r\n${bodyContent}`;
      python.stdin.write(requestData);
      python.stdin.end();
    });

    server.listen(0, () => {
      const { port } = server.address();
      const req = http.request({ port, path: event.path }, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          server.close(() => {
            callback(null, {
              statusCode: res.statusCode,
              headers: res.headers,
              body: data,
            });
          });
        });
      });
      req.on('error', (err) => {
        server.close(() => callback(err));
      });
      req.end();
    });
  };
}

module.exports = { createHandler };