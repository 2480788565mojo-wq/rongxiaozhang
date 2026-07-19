/// <reference types="vite/client" />

declare module '*.vue' {
  import { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'uview-plus';

declare function requirePlugin(name: string): any;

// Tests run in Vitest's Node host, but the app intentionally does not depend
// on the full Node type package. Keep the small read-only surface typed here.
declare module "node:fs" {
  interface Dirent {
    name: string;
    isDirectory(): boolean;
  }
  export function readFileSync(path: string, encoding: "utf8"): string;
  export function existsSync(path: string): boolean;
  export function readdirSync(path: string, options: { withFileTypes: true }): Dirent[];
}

declare module "node:path" {
  export function resolve(...paths: string[]): string;
  export function join(...paths: string[]): string;
  export function extname(path: string): string;
}

declare const process: {
  cwd(): string;
};
