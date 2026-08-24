import type {MediaResource} from "../shared/contracts.js";
import {normalizeError} from "../shared/errors.js";
import type {ExtractionOptions,Extractor} from "./extraction-types.js";
import {BrowserSnifferExtractor} from "./extractors/browser.js";
import {DirectExtractor,GenericHtmlExtractor,ManifestExtractor} from "./extractors/basic.js";
import {FxTwitterExtractor} from "./extractors/fxtwitter.js";
import {YtDlpExtractor} from "./extractors/yt-dlp.js";

export type {ExtractionOptions,Extractor} from "./extraction-types.js";
export {DirectExtractor,GenericHtmlExtractor,ManifestExtractor,discoverMediaUrls} from "./extractors/basic.js";
export {FxTwitterExtractor,parseFxTwitterResource} from "./extractors/fxtwitter.js";
export {YtDlpExtractor} from "./extractors/yt-dlp.js";
export {BrowserSnifferExtractor} from "./extractors/browser.js";

export class ExtractionPipeline{
  constructor(private extractors:Extractor[]=[new ManifestExtractor(),new DirectExtractor(),new YtDlpExtractor(),new FxTwitterExtractor(),new GenericHtmlExtractor(),new BrowserSnifferExtractor()]){}
  async extract(input:string,signal:AbortSignal,options:ExtractionOptions={}):Promise<MediaResource>{
    let url:URL;try{url=new URL(input);}catch{throw normalizeError({code:"INVALID_INPUT",message:"URL is invalid"},"input");}
    const failures:unknown[]=[];
    for(const extractor of this.extractors){try{const result=await extractor.extract(url,signal,options);if(result)return result;}catch(error){failures.push({extractor:extractor.name,error:normalizeError(error,"extract")});}}
    throw normalizeError({code:"UNSUPPORTED_MEDIA",message:"No extractor recognized this URL",failures},"extract");
  }
}
