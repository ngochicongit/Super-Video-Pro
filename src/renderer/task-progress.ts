export type ProgressTask={progress:number};

export function aggregateTaskProgress(tasks:ProgressTask[]){
  if(!tasks.length)return 0;
  return tasks.reduce((total,task)=>total+Math.max(0,Math.min(1,task.progress)),0)/tasks.length;
}
