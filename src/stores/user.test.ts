import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { ApiError, clearToken, getStoredToken } from '@/api/client';
import { getMe } from '@/api/auth';
import { useUserStore } from '@/stores/user';
import type { User } from '@/types';

// 只替换 token 读写，保留真实的 ApiError（restore 的 401 判定依赖 instanceof）。
vi.mock('@/api/client', async (importOriginal) => {
  const actual = (await importOriginal()) as typeof import('@/api/client');
  return {
    ...actual,
    getStoredToken: vi.fn(),
    clearToken: vi.fn(),
    saveToken: vi.fn(),
  };
});

vi.mock('@/api/auth', () => ({
  getMe: vi.fn(),
  wxLogin: vi.fn(),
  devLogin: vi.fn(),
}));

const TOKEN = 'stored-valid-token';
const mockUser: User = {
  id: 7,
  nickname: '荣小账用户',
  avatar_url: null,
  default_ledger_id: 3,
};

function createStore() {
  vi.mocked(getStoredToken).mockReturnValue(TOKEN);
  return useUserStore();
}

beforeEach(() => {
  vi.clearAllMocks();
  setActivePinia(createPinia());
});

describe('userStore.restore', () => {
  it('恢复成功：getMe 返回用户，token 保留且写入 user', async () => {
    vi.mocked(getMe).mockResolvedValue(mockUser);
    const store = createStore();

    const result = await store.restore();

    expect(getMe).toHaveBeenCalledTimes(1);
    expect(result).toEqual(mockUser);
    expect(store.user).toEqual(mockUser);
    expect(store.token).toBe(TOKEN);
    expect(store.isLoggedIn).toBe(true);
    expect(clearToken).not.toHaveBeenCalled();
  });

  it('401 ApiError：登出清 token，返回 null', async () => {
    vi.mocked(getMe).mockRejectedValue(new ApiError('登录已过期', 401));
    const store = createStore();

    const result = await store.restore();

    expect(result).toBeNull();
    // logout() 内部会调用 clearToken()，以此确认登出分支确实执行。
    expect(clearToken).toHaveBeenCalledTimes(1);
    expect(store.token).toBe('');
    expect(store.user).toBeNull();
    expect(store.isLoggedIn).toBe(false);
  });

  it('500 ApiError：保留 token，不登出，返回 null', async () => {
    vi.mocked(getMe).mockRejectedValue(new ApiError('服务器开小差了', 500));
    const store = createStore();

    const result = await store.restore();

    expect(result).toBeNull();
    expect(clearToken).not.toHaveBeenCalled();
    expect(store.token).toBe(TOKEN);
    expect(store.isLoggedIn).toBe(true);
    expect(store.user).toBeNull();
  });

  it('网络异常（非 ApiError）：保留 token，不登出，返回 null', async () => {
    vi.mocked(getMe).mockRejectedValue(new TypeError('Network Error'));
    const store = createStore();

    const result = await store.restore();

    expect(result).toBeNull();
    expect(clearToken).not.toHaveBeenCalled();
    expect(store.token).toBe(TOKEN);
    expect(store.isLoggedIn).toBe(true);
  });

  it('没有本地 token：不请求 getMe，返回 null', async () => {
    vi.mocked(getStoredToken).mockReturnValue('');
    const store = useUserStore();

    const result = await store.restore();

    expect(result).toBeNull();
    expect(getMe).not.toHaveBeenCalled();
    expect(clearToken).not.toHaveBeenCalled();
    expect(store.token).toBe('');
    expect(store.isLoggedIn).toBe(false);
  });

  it('非 401 的 4xx（403）也保留 token，不登出', async () => {
    vi.mocked(getMe).mockRejectedValue(new ApiError('无权限', 403));
    const store = createStore();

    const result = await store.restore();

    expect(result).toBeNull();
    expect(clearToken).not.toHaveBeenCalled();
    expect(store.token).toBe(TOKEN);
  });

  it('临时故障后 token 仍在，下一次 restore 可以恢复成功', async () => {
    vi.mocked(getMe).mockRejectedValueOnce(new ApiError('网关超时', 504));
    const store = createStore();

    expect(await store.restore()).toBeNull();
    expect(store.token).toBe(TOKEN);

    vi.mocked(getMe).mockResolvedValueOnce(mockUser);
    expect(await store.restore()).toEqual(mockUser);
    expect(store.token).toBe(TOKEN);
    expect(store.isLoggedIn).toBe(true);
  });
});

describe('userStore.ensureUser', () => {
  it('restore 非 401 失败后，ensureUser 可以补拉用户并恢复角色 UI', async () => {
    vi.mocked(getMe).mockRejectedValueOnce(new ApiError('服务器开小差', 500));
    const store = createStore();
    expect(await store.restore()).toBeNull();

    vi.mocked(getMe).mockResolvedValueOnce(mockUser);
    const result = await store.ensureUser();

    expect(result).toEqual(mockUser);
    expect(store.user).toEqual(mockUser);
    expect(store.token).toBe(TOKEN);
    expect(clearToken).not.toHaveBeenCalled();
  });

  it('ensureUser 遇到 401 仍会登出清 token', async () => {
    vi.mocked(getMe).mockRejectedValue(new ApiError('登录已过期', 401));
    const store = createStore();

    expect(await store.ensureUser()).toBeNull();
    expect(clearToken).toHaveBeenCalled();
    expect(store.token).toBe('');
    expect(store.isLoggedIn).toBe(false);
  });

  it('没有 token 时 ensureUser 不请求 getMe', async () => {
    vi.mocked(getStoredToken).mockReturnValue('');
    const store = useUserStore();

    expect(await store.ensureUser()).toBeNull();
    expect(getMe).not.toHaveBeenCalled();
  });

  it('并发调用 ensureUser 只发起一次 getMe，不会误登出', async () => {
    let resolveMe!: (value: User) => void;
    vi.mocked(getMe).mockImplementation(
      () => new Promise<User>((resolve) => { resolveMe = resolve; }),
    );
    const store = createStore();

    const first = store.ensureUser();
    const second = store.ensureUser();

    expect(getMe).toHaveBeenCalledTimes(1);

    resolveMe(mockUser);
    await expect(first).resolves.toEqual(mockUser);
    await expect(second).resolves.toBeNull();

    expect(getMe).toHaveBeenCalledTimes(1);
    expect(store.user).toEqual(mockUser);
    expect(store.token).toBe(TOKEN);
    expect(clearToken).not.toHaveBeenCalled();
  });

  it('已有 user 时 ensureUser 直接返回，不重复请求 getMe', async () => {
    vi.mocked(getMe).mockResolvedValue(mockUser);
    const store = createStore();
    store.user = mockUser;

    expect(await store.ensureUser()).toEqual(mockUser);
    expect(getMe).not.toHaveBeenCalled();
  });
});
