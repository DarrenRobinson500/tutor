const MonacoWebpackPlugin = require("monaco-editor-webpack-plugin");

module.exports = {
  webpack: {
    plugins: {
      add: [
        new MonacoWebpackPlugin({
          // Only the languages actually used in the editor (see SectionedEditorPanel/EditorPanel).
          languages: ["yaml"],
        }),
      ],
    },
  },
};
