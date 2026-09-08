import { loadConfig } from "./config.js";
import { buildApp } from "./app.js";

async function main(): Promise<void> {
  const cfg = await loadConfig();
  const app = await buildApp(cfg);

  const port = cfg.port;
  await app.listen({ port, host: "0.0.0.0" });
  app.log.info(`node-gateway listening on ${port}, upstream=${cfg.fastapiUrl}`);
}

main().catch((e) => {
  console.error("node-gateway boot failed", e);
  process.exit(1);
});
