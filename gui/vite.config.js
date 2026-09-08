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
        "/upload": {
          target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
        "/parse": {
          target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
        "/generate": {
          target: env.VITE_API_PROXY_TARGET || env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
        "/task": {
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
      modulePreload: false,
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
