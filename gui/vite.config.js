import { defineConfig, loadEnv } from "vite"
import vue from "@vitejs/plugin-vue"
import path from "path"

function singleFileHtmlPlugin() {
  const escapeInlineScript = (code) => {
    return code
      .replace(/<\/script/gi, "<\\/script")
      .replace(/<!--/g, "<\\!--")
  }
  const escapeInlineStyle = (code) => {
    return String(code).replace(/<\/style/gi, "<\\/style")
  }

  return {
    name: "ga-single-file-html",
    apply: "build",
    enforce: "post",

    // 单文件构建（inlineDynamicImports）下，Vite 可能不会把动态导入注入的
    // __VITE_PRELOAD__ 占位符替换成真实依赖列表，产物里会留下未定义标识符，
    // 浏览器执行到懒加载路由时抛 ReferenceError。
    // 所有 chunk 已内联进同一个文件，预加载依赖没有意义，直接置为 void 0。
    renderChunk(code) {
      if (!code.includes("__VITE_PRELOAD__")) return null
      return {
        code: code.replace(/__VITE_PRELOAD__/g, "void 0"),
        map: null,
      }
    },

    generateBundle(_options, bundle) {
      const htmlAsset = Object.values(bundle).find((item) => item.type === "asset" && item.fileName === "index.html")
      if (!htmlAsset) return

      let html = String(htmlAsset.source)
      for (const [fileName, item] of Object.entries(bundle)) {
        if (item.type === "chunk" && fileName.endsWith(".js")) {
          html = html.replace(
            new RegExp(`<script[^>]*src=["'][^"']*${fileName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}["'][^>]*></script>`),
            () => `<script type="module">\n${escapeInlineScript(item.code)}\n</script>`,
          )
          delete bundle[fileName]
        }
        if (item.type === "asset" && fileName.endsWith(".css")) {
          html = html.replace(
            new RegExp(`<link[^>]*href=["'][^"']*${fileName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}["'][^>]*>`),
            () => `<style>\n${escapeInlineStyle(item.source)}\n</style>`,
          )
          delete bundle[fileName]
        }
      }
      htmlAsset.source = html

      // 构建期断言：占位符残留只会在浏览器里炸，这里直接让构建失败。
      const leftovers = ["__VITE_PRELOAD__", "__VITE_IS_MODERN__"].filter((marker) => html.includes(marker))
      if (leftovers.length) {
        throw new Error(`single-file build left unresolved Vite placeholders: ${leftovers.join(", ")}`)
      }
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [vue(), singleFileHtmlPlugin()],
    base: "./",

    resolve: {
      alias: {
        "@": path.resolve(__dirname, "src"),
        "@components": path.resolve(__dirname, "src/components"),
        "@views": path.resolve(__dirname, "src/views"),
        "@api": path.resolve(__dirname, "src/api"),
        "@utils": path.resolve(__dirname, "src/utils"),
        "@assets": path.resolve(__dirname, "src/assets"),
      },
    },

    server: {
      port: 5173,
      proxy: {
        "/fcgi-bin": {
          target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
        "/api": {
          target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },

    build: {
      outDir: "..",
      assetsDir: "gui-assets",
      sourcemap: mode === "development",
      emptyOutDir: false,
      cssCodeSplit: false,
      assetsInlineLimit: 100000000,
      modulePreload: { polyfill: false },
      rollupOptions: {
        output: {
          inlineDynamicImports: true,
          entryFileNames: "gui-assets/[name].js",
          chunkFileNames: "gui-assets/[name].js",
          assetFileNames: "gui-assets/[name].[ext]",
        },
      },
    },
  }
})
