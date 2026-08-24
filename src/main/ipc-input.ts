import type {z} from "zod";
import {ipcContract,type IpcChannel} from "../shared/ipc.js";

export type IpcInput<C extends IpcChannel>=z.output<(typeof ipcContract)[C]["input"]>;
