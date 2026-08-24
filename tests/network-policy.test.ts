import {describe,expect,it} from "vitest";
import {assertOutboundUrl,readBoundedText} from "../src/main/network-policy";

describe("outbound network policy",()=>{
  it("allows ordinary HTTP and HTTPS URLs",()=>{expect(assertOutboundUrl("https://example.com/video").hostname).toBe("example.com");expect(assertOutboundUrl("http://127.0.0.1/fixture").hostname).toBe("127.0.0.1");});
  it("rejects credentials and link-local metadata targets",()=>{expect(()=>assertOutboundUrl("https://user:secret@example.com/video")).toThrow(/credentials/);expect(()=>assertOutboundUrl("http://169.254.169.254/latest/meta-data")).toThrow(/Link-local/);});
  it("rejects a declared response larger than its byte budget",async()=>{const response=new Response("small",{headers:{"content-length":"1001"}});await expect(readBoundedText(response,1000)).rejects.toThrow(/byte limit/);});
  it("enforces the byte budget while streaming without content-length",async()=>{const response=new Response(new Uint8Array(1001));await expect(readBoundedText(response,1000)).rejects.toThrow(/byte limit/);});
});
