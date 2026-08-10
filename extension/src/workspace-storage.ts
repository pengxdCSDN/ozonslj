const SELECTED_WORKSPACE_KEY = "selectedWorkspaceId:v1";

export async function loadSelectedWorkspaceId(): Promise<string | null> {
  try {
    if (globalThis.chrome?.storage?.local) {
      const stored = await chrome.storage.local.get(SELECTED_WORKSPACE_KEY);
      const value = stored[SELECTED_WORKSPACE_KEY];
      return typeof value === "string" ? value : null;
    }
    return globalThis.localStorage?.getItem(SELECTED_WORKSPACE_KEY) ?? null;
  } catch {
    return null;
  }
}

export async function saveSelectedWorkspaceId(workspaceId: string): Promise<void> {
  try {
    if (globalThis.chrome?.storage?.local) {
      await chrome.storage.local.set({ [SELECTED_WORKSPACE_KEY]: workspaceId });
      return;
    }
    globalThis.localStorage?.setItem(SELECTED_WORKSPACE_KEY, workspaceId);
  } catch {
    // 选择仍在当前页面内生效，存储不可用不应阻断店铺操作。
  }
}
