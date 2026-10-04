export const judgeDemo:{email:string;password:string;imageHash:string};
export function seedJudgeDemo(options:{api:(body:object)=>Promise<Record<string,any>>;upload:(path:string,image:Blob,digest:string)=>Promise<void>;fetcher?:typeof fetch}):Promise<Record<string,any>>;
