global.configuration = {
    DEBUG: false,
    showOfflineUsers: true, // When true all users will always be shown. Offline users will be shown as away on clients that support away-notify.
    discordToken: 'BOT TOKEN HERE',
    tlsEnabled: false,
    tlsOptions: {
      keyPath: '/path/to/key.pem',
      certPath: '/path/to/cert.pem'
    },
    handleCode: true, 
    githubToken: 'GITHUB TOKEN HERE',
    ircServer: {
        listenPort: 6667,
        hostname: '127.0.0.1',
        username: 'BOT USERNAME HERE' 
    }
};

