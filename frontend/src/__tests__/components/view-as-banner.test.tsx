import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViewAsBanner } from "@/components/view-as-banner";

const switchScope = vi.fn();
let mockUser: Record<string, unknown> | null = null;

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ user: mockUser, switchScope }),
}));

describe("ViewAsBanner", () => {
  beforeEach(() => {
    switchScope.mockReset();
    mockUser = null;
  });

  it.each([
    ["manager", "Viendo como manager (solo lectura)"],
    ["worker", "Viendo como worker (solo lectura)"],
  ])("muestra el banner para viewAs=%s", (viewAs, text) => {
    mockUser = { id: "pa", isReadOnlyView: true, viewAs, activeCompanyId: "c1" };

    render(<ViewAsBanner />);

    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it("Salir del modo llama a switchScope con la empresa activa", () => {
    mockUser = {
      id: "pa",
      isReadOnlyView: true,
      viewAs: "manager",
      activeCompanyId: "c1",
    };

    render(<ViewAsBanner />);
    fireEvent.click(screen.getByRole("button", { name: "Salir del modo" }));

    expect(switchScope).toHaveBeenCalledWith("c1");
  });

  it("no se renderiza sin modo de solo lectura", () => {
    mockUser = { id: "u", isReadOnlyView: false, viewAs: null, activeCompanyId: "c1" };

    const { container } = render(<ViewAsBanner />);

    expect(container).toBeEmptyDOMElement();
  });

  it("no se renderiza sin usuario", () => {
    const { container } = render(<ViewAsBanner />);

    expect(container).toBeEmptyDOMElement();
  });
});
