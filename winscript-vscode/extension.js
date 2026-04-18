const { LanguageClient } = require('vscode-languageclient/node');

let client;

function activate(context) {
    const serverOptions = {
        command: 'python3',
        args: [context.asAbsolutePath('server/server.py')]
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'winscript' }]
    };

    client = new LanguageClient(
        'winscriptLanguageServer',
        'WinScript Language Server',
        serverOptions,
        clientOptions
    );

    client.start();
}

function deactivate() {
    if (!client) {
        return undefined;
    }
    return client.stop();
}

module.exports = {
    activate,
    deactivate
};
