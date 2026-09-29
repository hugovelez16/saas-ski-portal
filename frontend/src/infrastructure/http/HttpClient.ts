import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { IHttpClient, RequestConfig } from '../../core/ports/IHttpClient';

export class AxiosHttpClient implements IHttpClient {
  private client: AxiosInstance;

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || '/api') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });
  }

  private mapConfig(config?: RequestConfig): AxiosRequestConfig {
    if (!config) return {};
    return {
      headers: config.headers,
      params: config.params,
      withCredentials: config.withCredentials !== undefined ? config.withCredentials : true,
    };
  }

  async get<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, this.mapConfig(config));
    return response.data;
  }

  async post<T>(url: string, data?: unknown, config?: RequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, this.mapConfig(config));
    return response.data;
  }

  async put<T>(url: string, data?: unknown, config?: RequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, this.mapConfig(config));
    return response.data;
  }

  async delete<T>(url: string, config?: RequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, this.mapConfig(config));
    return response.data;
  }
}

export const httpClient = new AxiosHttpClient();
