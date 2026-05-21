function ensureApi() {
  if (!(window as any).pywebview?.api) throw new Error("pywebview API is not available")
}

async function callApi(method: string, ...args: any[]): Promise<any> {
  ensureApi()
  return await (window as any).pywebview.api[method](...args)
}

export { callApi }
