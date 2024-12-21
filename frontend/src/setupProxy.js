const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://0.0.0.0:8001/api',
      changeOrigin: true,
      secure: false,
      allowedHosts: [
        'localhost',
        '0.0.0.0',
        '.swarmchat.me',
        'dev.swarmchat.me'
      ]
    })
  );
};
