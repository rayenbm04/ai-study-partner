module.exports = function (api) {
  api.cache(true);
  return {
    presets: [["babel-preset-expo", { jsxImportSource: "nativewind" }], "nativewind/babel"],
    plugins: [
      // Expo/Metro's built-in tsconfig "paths" resolution isn't picking up
      // "@/*" here (SDK 57) — this rewrites the aliases at compile time
      // instead, which doesn't depend on Metro's resolver internals.
      ["module-resolver", { root: ["."], alias: { "@": "." } }],
    ],
  };
};
