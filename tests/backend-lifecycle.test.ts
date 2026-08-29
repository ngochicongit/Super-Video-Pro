import {describe,expect,it} from "vitest";
import {BackendLifecycle} from "../src/main/backend-lifecycle";
describe("backend lifecycle",()=>{it("starts unowned",()=>{expect(new BackendLifecycle({url:"http://127.0.0.1:1"}).ownedByElectron).toBe(false);});});
