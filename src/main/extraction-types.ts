import type {MediaResource} from "../shared/contracts.js";
export type ExtractionOptions={cookiesFromBrowser?:"none"|"edge"|"chrome"|"firefox";allowThirdPartyXFallback?:boolean};
export type Extractor={name:string;extract(url:URL,signal:AbortSignal,options?:ExtractionOptions):Promise<MediaResource|null>};
