const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectUpdate {
  name?: string | null;
  description?: string | null;
}

export interface Asset {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  ingested: boolean;
  asset_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface GenerationRequest {
  project_id: string;
  brief: string;
  brand_tone?: string | null;
  audience?: string | null;
  objective?: string | null;
  channels?: string[] | null;
}

export interface ContentVariant {
  variant_type: string;
  content: string;
  character_count: number;
  word_count: number;
}

export interface GenerationMetadata {
  model: string;
  model_info: Record<string, unknown>;
  project_id?: string | null;
  tokens_used?: number | null;
  generation_time?: number | null;
}

export interface GenerationResponse {
  generation_id: string;
  short_form: string;
  long_form: string;
  cta: string;
  metadata: GenerationMetadata;
  variants?: ContentVariant[] | null;
}

export interface GenerationUpdateRequest {
  short_form?: string | null;
  long_form?: string | null;
  cta?: string | null;
}

export interface GenerationUpdateResponse {
  message: string;
  updated: GenerationResponse;
}

export interface GenerationAcceptedResponse {
  message: string;
  generation_id: string;
  status: "pending" | "processing" | "completed" | "failed";
}

export interface AssistantQueryRequest {
  project_id: string;
  question: string;
  top_k?: number;
  include_citations?: boolean;
}

export interface Citation {
  index: number;
  text: string;
  asset_id: string;
  chunk_index: number;
  score: number;
  metadata?: Record<string, unknown> | null;
}

export interface AssistantQueryMetadata {
  model: string;
  provider: string;
  project_id: string;
  chunks_retrieved: number;
  has_context: boolean;
}

export interface AssistantQueryResponse {
  answer: string;
  citations: Citation[];
  metadata: AssistantQueryMetadata;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    // Only set Content-Type for non-FormData requests
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = "An error occurred";
      try {
        const error = await response.json();
        // Handle different error response formats
        const extractedMessage =
          error.detail ||
          error.message ||
          error.error ||
          (typeof error === "string" ? error : null);
        // Ensure extractedMessage is converted to a string
        if (extractedMessage !== null && extractedMessage !== undefined) {
          errorMessage = typeof extractedMessage === "string" 
            ? extractedMessage 
            : String(extractedMessage);
        } else {
          errorMessage = response.statusText || "An error occurred";
        }
      } catch {
        // If JSON parsing fails, use status text
        errorMessage = response.statusText || "An error occurred";
      }
      // Ensure errorMessage is always a non-empty string
      if (!errorMessage || errorMessage.trim() === "") {
        errorMessage = "An error occurred";
      }
      throw new Error(errorMessage);
    }

    // Handle 204 No Content responses
    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  setToken(token: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem("access_token", token);
  }

  removeToken(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
  }

  async signup(data: SignupRequest): Promise<User> {
    return this.request<User>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    this.setToken(response.access_token);
    return response;
  }

  logout(): void {
    this.removeToken();
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>("/api/auth/me");
  }

  // Project methods
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>("/api/projects");
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/api/projects/${id}`);
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    return this.request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    return this.request<Project>(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: string): Promise<void> {
    await this.request(`/api/projects/${id}`, {
      method: "DELETE",
    });
  }

  // Asset methods
  async getAssets(projectId: string): Promise<Asset[]> {
    return this.request<Asset[]>(`/api/projects/${projectId}/assets`);
  }

  async getAsset(projectId: string, assetId: string): Promise<Asset> {
    return this.request<Asset>(`/api/projects/${projectId}/assets/${assetId}`);
  }

  async uploadAsset(projectId: string, file: File): Promise<Asset> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<Asset>(`/api/projects/${projectId}/assets`, {
      method: "POST",
      body: formData,
    });
  }

  async updateAsset(
    projectId: string,
    assetId: string,
    data: Partial<{
      filename: string;
      content_type: string;
      ingested: boolean;
      metadata: Record<string, unknown>;
    }>
  ): Promise<Asset> {
    return this.request<Asset>(`/api/projects/${projectId}/assets/${assetId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteAsset(projectId: string, assetId: string): Promise<void> {
    await this.request(`/api/projects/${projectId}/assets/${assetId}`, {
      method: "DELETE",
    });
  }

  async downloadAsset(projectId: string, assetId: string): Promise<Blob> {
    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(
      `${this.baseUrl}/api/projects/${projectId}/assets/${assetId}/download`,
      { headers }
    );

    if (!response.ok) {
      let errorMessage = "An error occurred";
      try {
        const error = await response.json();
        // Handle different error response formats
        const extractedMessage =
          error.detail ||
          error.message ||
          error.error ||
          (typeof error === "string" ? error : null);
        // Ensure extractedMessage is converted to a string
        if (extractedMessage !== null && extractedMessage !== undefined) {
          errorMessage = typeof extractedMessage === "string" 
            ? extractedMessage 
            : String(extractedMessage);
        } else {
          errorMessage = response.statusText || "An error occurred";
        }
      } catch {
        // If JSON parsing fails, use status text
        errorMessage = response.statusText || "An error occurred";
      }
      // Ensure errorMessage is always a non-empty string
      if (!errorMessage || errorMessage.trim() === "") {
        errorMessage = "An error occurred";
      }
      throw new Error(errorMessage);
    }

    return response.blob();
  }

  // Generation methods
  async generateContent(data: GenerationRequest): Promise<GenerationAcceptedResponse> {
    return this.request<GenerationAcceptedResponse>("/api/generate", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getGenerationRecords(projectId: string): Promise<GenerationResponse[]> {
    return this.request<GenerationResponse[]>(`/api/projects/${projectId}/generation-records`);
  }

  async getGenerationRecord(generationId: string): Promise<GenerationResponse> {
    return this.request<GenerationResponse>(`/api/generate/${generationId}`);
  }

  async updateGenerationRecord(
    generationId: string,
    data: GenerationUpdateRequest
  ): Promise<GenerationUpdateResponse> {
    return this.request<GenerationUpdateResponse>(`/api/generate/${generationId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async updateGeneratedContent(
    data: GenerationUpdateRequest
  ): Promise<GenerationUpdateResponse> {
    return this.request<GenerationUpdateResponse>("/api/generate/update", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  // Assistant methods
  async queryAssistant(data: AssistantQueryRequest): Promise<AssistantQueryResponse> {
    return this.request<AssistantQueryResponse>("/api/assistant/query", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient(API_URL);

