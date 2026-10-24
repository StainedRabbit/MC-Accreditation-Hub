/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_R2_DIRECT_UPLOADS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
