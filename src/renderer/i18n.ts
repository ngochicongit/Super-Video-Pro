import vi from "../locales/vi.json";
export type TranslationKey=keyof typeof vi;
export function t(key:TranslationKey){return vi[key];}
