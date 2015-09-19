var definePlugin = new webpack.DefinePlugin({
    __DEV__: JSON.stringify(JSON.parse(process.env.BUILD_DEV || 'true')),
    __PRERELEASE__: JSON.stringify(JSON.parse(process.env.PRERELEASE || 'false'))
});

module.exports = {
    entry: {
        User: './main.js',
        Organization: './organization.js'
    },
    ouput: {
        path: './build',
        filename: 'bundle.js'
    },
    module: {
        loaders: {
            { test: /\.css$/, loader: 'style-loader!css-loader' },
            { test: /\.(png|jpg)$/, loader: 'url-loader?limit=8192' },
            { test: /\.js$/, loader: ['react-hot', 'babel-loader'] },
            { test: /\.scss$/, loader: 'style!css!sass' }
        }
    },
    plugins: [definePlugin]
};
