module.exports = [
"[externals]/child_process [external] (child_process, cjs, async loader)", ((__turbopack_context__) => {

__turbopack_context__.v((parentImport) => {
    return Promise.all([
  "server/chunks/[externals]_child_process_17eio63._.js"
].map((chunk) => __turbopack_context__.l(chunk))).then(() => {
        return parentImport("[externals]/child_process [external] (child_process, cjs)");
    });
});
}),
"[externals]/util [external] (util, cjs, async loader)", ((__turbopack_context__) => {

__turbopack_context__.v((parentImport) => {
    return Promise.all([
  "server/chunks/[externals]_util_1jlmhhy._.js"
].map((chunk) => __turbopack_context__.l(chunk))).then(() => {
        return parentImport("[externals]/util [external] (util, cjs)");
    });
});
}),
];