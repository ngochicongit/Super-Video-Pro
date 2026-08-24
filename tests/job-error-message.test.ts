import {describe,expect,it} from "vitest";
import {jobErrorMessage} from "../src/renderer/job-row";
describe("actionable job errors",()=>{it("maps known codes to Vietnamese guidance",()=>expect(jobErrorMessage({code:"LOW_DISK",message:"raw"})).toContain("dung lượng"));it("recognizes locked browser cookie databases",()=>expect(jobErrorMessage({code:"UNKNOWN",message:"Could not copy Chrome cookie database"})).toContain("cookie"));it("recognizes provider access failures",()=>expect(jobErrorMessage({code:"UNKNOWN",message:"HTTP Error 403: Forbidden"})).toContain("từ chối"));});
