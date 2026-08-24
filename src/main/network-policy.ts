const redirectStatuses=new Set([301,302,303,307,308]);

export function assertOutboundUrl(input:string|URL){
  const url=input instanceof URL?new URL(input):new URL(input);
  if(!["http:","https:"].includes(url.protocol))throw new Error("Only HTTP and HTTPS URLs are allowed");
  if(url.username||url.password)throw new Error("URLs containing credentials are not allowed");
  const host=url.hostname.toLowerCase().replace(/^\[|\]$/g,"");
  if(host==="0.0.0.0"||host==="::"||host.startsWith("169.254.")||host.startsWith("fe80:"))throw new Error("Link-local and unspecified network targets are not allowed");
  return url;
}

export async function fetchOutbound(input:string|URL,init:RequestInit={},timeoutMs=15000){
  let url=assertOutboundUrl(input);
  for(let redirects=0;redirects<=5;redirects++){
    const signal=init.signal?AbortSignal.any([init.signal,AbortSignal.timeout(timeoutMs)]):AbortSignal.timeout(timeoutMs);
    const response=await fetch(url,{...init,signal,redirect:"manual"});
    if(!redirectStatuses.has(response.status))return response;
    const location=response.headers.get("location");response.body?.cancel();
    if(!location)throw new Error("Redirect response is missing a location");
    url=assertOutboundUrl(new URL(location,url));
  }
  throw new Error("Too many redirects");
}

export async function readBoundedText(response:Response,maxBytes:number){
  const declared=Number(response.headers.get("content-length")??0);
  if(declared>maxBytes)throw new Error(`Response exceeds ${maxBytes} byte limit`);
  if(!response.body)return "";
  const reader=response.body.getReader();const chunks:Uint8Array[]=[];let total=0;
  try{for(;;){const {done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>maxBytes)throw new Error(`Response exceeds ${maxBytes} byte limit`);chunks.push(value);}}
  catch(error){await reader.cancel().catch(()=>undefined);throw error;}
  const joined=new Uint8Array(total);let offset=0;for(const chunk of chunks){joined.set(chunk,offset);offset+=chunk.byteLength;}
  return new TextDecoder().decode(joined);
}
