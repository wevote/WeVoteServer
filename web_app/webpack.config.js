module.exports = {
  entry: './app/App.js',
  contentBase: './build',
  output: {
    filename: '[name]/bundle.js',
    publicPath: '/',
    path: path.resolve(__dirname, 'build')
  },
  module: {
    preLoaders: [
      {
        test: /\.jsx?$/,
        loader: 'eslint',
        exclude: /node_modules|build/
      }
    ],
    loaders: [
      {
        test: /\.jsx?$/,
        loaders: ENV === 'development'
          ? ['react-hot', 'babel']
          : ['babel']
        exclude: /(node_modules|build)/,
      }
    ]
  },
  resolve: {
    root: [path.resolve('./app')],
    extensions: ['', '.js', '.jsx']
  },
  plugins: ENV === 'development'
    ? [new webpack.HotModuleReplacementPlugin()]
    : [],
  eslint: {configFile: '.eslintrc'},
  node: {
    fs: 'empty'
  }
};
