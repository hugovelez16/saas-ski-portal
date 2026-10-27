import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AxiosError, AxiosHeaders, InternalAxiosRequestConfig } from "axios";
import api, {
  setErrorNotifier,
  formatErrorDetail,
  isSuspendedCompanyError,
  describeLoadError,
  SUSPENDED_COMPANY_DETAIL,
  SUSPENDED_COMPANY_MESSAGE,
} from "@/lib/api";

function failWith(status: number, data: unknown) {
  api.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    throw new AxiosError(
      `status ${status}`,
      "ERR_BAD_RESPONSE",
      config,
      null,
      {
        status,
        statusText: String(status),
        data,
        headers: {},
        config: { ...config, headers: new AxiosHeaders() },
      },
    );
  };
}

describe("api response interceptor", () => {
  const notifier = vi.fn();

  beforeEach(() => {
    notifier.mockReset();
    setErrorNotifier(notifier);
  });

  afterEach(() => {
    setErrorNotifier(null);
  });

  it.each([
    [403, "Sin permiso"],
    [404, "No encontrado"],
    [409, "Conflicto"],
    [422, "Datos no validos"],
    [500, "Error del servidor"],
    [503, "Error del servidor"],
  ])("status %i notifica con titulo %s y el detail del backend", async (status, title) => {
    failWith(status, { detail: "Mensaje del backend" });

    await expect(api.get("/x")).rejects.toBeTruthy();

    expect(notifier).toHaveBeenCalledTimes(1);
    expect(notifier).toHaveBeenCalledWith({
      variant: "destructive",
      title,
      description: "Mensaje del backend",
    });
  });

  it("une de forma legible el detail lista de FastAPI 422", async () => {
    failWith(422, {
      detail: [
        { msg: "Field required", loc: ["body", "name"] },
        { msg: "Input should be a valid number", loc: ["body", "rate"] },
      ],
    });

    await expect(api.post("/x", {})).rejects.toBeTruthy();

    const arg = notifier.mock.calls[0][0];
    expect(arg.title).toBe("Datos no validos");
    expect(arg.description).toBe(
      "name: Field required; rate: Input should be a valid number",
    );
  });

  it("usa un texto generico si no hay detail", async () => {
    failWith(500, {});

    await expect(api.get("/x")).rejects.toBeTruthy();

    const arg = notifier.mock.calls[0][0];
    expect(typeof arg.description).toBe("string");
    expect(arg.description.length).toBeGreaterThan(0);
  });

  it("no notifica con meta.silent", async () => {
    failWith(403, { detail: "No tienes acceso a esta empresa" });

    await expect(api.get("/x", { meta: { silent: true } })).rejects.toBeTruthy();

    expect(notifier).not.toHaveBeenCalled();
  });

  it("no notifica en 401 (lo gestiona AuthContext)", async () => {
    failWith(401, { detail: "Not authenticated" });

    await expect(api.get("/x")).rejects.toBeTruthy();

    expect(notifier).not.toHaveBeenCalled();
  });

  it("no notifica si el error no tiene respuesta (red)", async () => {
    api.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      throw new AxiosError("Network Error", "ERR_NETWORK", config);
    };

    await expect(api.get("/x")).rejects.toBeTruthy();

    expect(notifier).not.toHaveBeenCalled();
  });

  it("propaga el error original para que el llamador lo gestione", async () => {
    failWith(409, { detail: "Conflicto" });

    await expect(api.get("/x")).rejects.toMatchObject({
      response: { status: 409 },
    });
  });

  it("sin notificador registrado no falla", async () => {
    setErrorNotifier(null);
    failWith(500, { detail: "boom" });

    await expect(api.get("/x")).rejects.toBeTruthy();
  });
});

describe("empresa suspendida", () => {
  const suspended = { response: { status: 403, data: { detail: SUSPENDED_COMPANY_DETAIL } } };

  it("isSuspendedCompanyError reconoce solo el 403 con el detail exacto", () => {
    expect(isSuspendedCompanyError(suspended)).toBe(true);
    expect(isSuspendedCompanyError({ response: { status: 403, data: { detail: "otro" } } })).toBe(false);
    expect(isSuspendedCompanyError({ response: { status: 404, data: { detail: SUSPENDED_COMPANY_DETAIL } } })).toBe(false);
    expect(isSuspendedCompanyError(new Error("x"))).toBe(false);
  });

  it("describeLoadError da el mensaje de suspension, el detail o el texto por defecto", () => {
    expect(describeLoadError(suspended, "fallback")).toBe(SUSPENDED_COMPANY_MESSAGE);
    expect(describeLoadError({ response: { status: 403, data: { detail: "Sin acceso" } } }, "fallback")).toBe("Sin acceso");
    expect(describeLoadError(new Error("x"), "fallback")).toBe("fallback");
  });
});

describe("formatErrorDetail", () => {
  it("devuelve la cadena tal cual", () => {
    expect(formatErrorDetail("hola")).toBe("hola");
  });

  it("devuelve cadena vacia para valores no soportados", () => {
    expect(formatErrorDetail(undefined)).toBe("");
    expect(formatErrorDetail(42)).toBe("");
  });

  it("omite 'body' y 'query' del loc y tolera entradas sin msg", () => {
    expect(
      formatErrorDetail([{ msg: "x", loc: ["query", "page"] }, { loc: ["body"] }]),
    ).toBe("page: x");
  });
});
