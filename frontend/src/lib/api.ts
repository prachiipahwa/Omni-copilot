const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
    this.name = 'ApiError';
  }
}

export class ApiClient {
  private static csrfToken: string | null = null;
  private static csrfPromise: Promise<void> | null = null;

  /**
   * Bootstraps the CSRF token. Uses a singleton promise to prevent
   * race conditions where multiple rapid requests trigger multiple CSRF fetches.
   */
  static async bootstrapCsrf(): Promise<void> {
    if (this.csrfToken) return;
    if (this.csrfPromise) return this.csrfPromise;

    this.csrfPromise = (async () => {
      try {
        // CSRF path hardened to match backend auth endpoints
        const response = await fetch(`${API_BASE_URL}/auth/csrf`, { 
          method: 'GET',
          credentials: 'include' 
        });
        if (response.ok) {
          const data = await response.json();
          this.csrfToken = data.csrf_token;
        }
      } catch (e) {
        console.error('Failed to bootstrap CSRF token', e);
      } finally {
        this.csrfPromise = null;
      }
    })();

    return this.csrfPromise;
  }

  static async request<TResponse>(endpoint: string, options: RequestInit = {}): Promise<TResponse> {
    const isMutating = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase() || 'GET');
    
    // Prevent unauthenticated mutating race conditions
    if (isMutating && !this.csrfToken) {
      await this.bootstrapCsrf();
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (isMutating && this.csrfToken) {
      headers['X-CSRF-Token'] = this.csrfToken;
    }

    const config: RequestInit = {
      ...options,
      headers,
      credentials: 'include' as RequestCredentials,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
      throw new ApiError(response.status, errorData.detail);
    }

    return response.json() as Promise<TResponse>;
  }

  static get<TResponse>(endpoint: string, options?: RequestInit): Promise<TResponse> {
    return this.request<TResponse>(endpoint, { ...options, method: 'GET' });
  }

  static post<TRequest, TResponse>(endpoint: string, body: TRequest, options?: RequestInit): Promise<TResponse> {
    return this.request<TResponse>(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) });
  }
}
