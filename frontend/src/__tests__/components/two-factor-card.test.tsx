import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const toast = vi.fn();
const checkAuth = vi.fn();
let mockUser: { is2faEnabled: boolean } | null = { is2faEnabled: false };

vi.mock("@/context/AuthContext", () => ({
    useAuth: () => ({ user: mockUser, checkAuth }),
}));

vi.mock("@/hooks/use-toast", () => ({
    useToast: () => ({ toast }),
}));

vi.mock("qrcode.react", () => ({
    QRCodeSVG: ({ value }: { value: string }) => <div data-testid="qr">{value}</div>,
}));

vi.mock("@/lib/api/users", () => ({
    setup2fa: vi.fn(),
    activate2fa: vi.fn(),
    disable2fa: vi.fn(),
}));

import { TwoFactorCard, twoFactorErrorMessage } from "@/components/auth/two-factor-card";
import { setup2fa, activate2fa, disable2fa } from "@/lib/api/users";

const SETUP = { secret: "JBSWY3DPEHPK3PXP", qrCodeUri: "otpauth://totp/Vesotel:user@vesotel.com?secret=JBSWY3DPEHPK3PXP" };

describe("TwoFactorCard", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUser = { is2faEnabled: false };
    });

    it("shows the inactive state with an enable button", () => {
        render(<TwoFactorCard />);

        expect(screen.getByText("Inactive")).toBeTruthy();
        expect(screen.getByRole("button", { name: /enable two-factor/i })).toBeTruthy();
    });

    it("shows the active state with a disable button", () => {
        mockUser = { is2faEnabled: true };
        render(<TwoFactorCard />);

        expect(screen.getByText("Active")).toBeTruthy();
        expect(screen.getByRole("button", { name: /disable two-factor/i })).toBeTruthy();
    });

    it("runs the activation flow: setup, QR, code and refresh", async () => {
        vi.mocked(setup2fa).mockResolvedValue(SETUP);
        vi.mocked(activate2fa).mockResolvedValue({ message: "ok" });
        render(<TwoFactorCard />);

        fireEvent.click(screen.getByRole("button", { name: /enable two-factor/i }));

        await waitFor(() => expect(screen.getByTestId("qr").textContent).toBe(SETUP.qrCodeUri));
        expect(screen.getByText(SETUP.secret)).toBeTruthy();

        const confirmButton = screen.getByRole("button", { name: "Enable" });
        expect((confirmButton as HTMLButtonElement).disabled).toBe(true);

        fireEvent.change(screen.getByLabelText("Verification code"), { target: { value: "123456" } });
        fireEvent.click(confirmButton);

        await waitFor(() => expect(activate2fa).toHaveBeenCalledWith("123456"));
        await waitFor(() => expect(checkAuth).toHaveBeenCalled());
        expect(toast).toHaveBeenCalledWith({ title: "Two-factor authentication enabled" });
    });

    it("shows an error and keeps the dialog open when the code is wrong", async () => {
        vi.mocked(setup2fa).mockResolvedValue(SETUP);
        vi.mocked(activate2fa).mockRejectedValue({ response: { status: 400 } });
        render(<TwoFactorCard />);

        fireEvent.click(screen.getByRole("button", { name: /enable two-factor/i }));
        await waitFor(() => screen.getByTestId("qr"));

        fireEvent.change(screen.getByLabelText("Verification code"), { target: { value: "000000" } });
        fireEvent.click(screen.getByRole("button", { name: "Enable" }));

        await waitFor(() => expect(screen.getByText("Invalid or expired code.")).toBeTruthy());
        expect(checkAuth).not.toHaveBeenCalled();
    });

    it("disables 2FA by sending the current code", async () => {
        mockUser = { is2faEnabled: true };
        vi.mocked(disable2fa).mockResolvedValue({ message: "2FA disabled" });
        render(<TwoFactorCard />);

        fireEvent.click(screen.getByRole("button", { name: /disable two-factor/i }));
        fireEvent.change(screen.getByLabelText("Verification code"), { target: { value: "654321" } });
        fireEvent.click(screen.getByRole("button", { name: "Disable" }));

        await waitFor(() => expect(disable2fa).toHaveBeenCalledWith("654321"));
        await waitFor(() => expect(checkAuth).toHaveBeenCalled());
    });

    it("only accepts digits in the code field", async () => {
        mockUser = { is2faEnabled: true };
        render(<TwoFactorCard />);

        fireEvent.click(screen.getByRole("button", { name: /disable two-factor/i }));
        const input = screen.getByLabelText("Verification code") as HTMLInputElement;
        fireEvent.change(input, { target: { value: "12ab34" } });

        expect(input.value).toBe("1234");
    });
});

describe("twoFactorErrorMessage", () => {
    it("maps HTTP statuses to readable messages", () => {
        expect(twoFactorErrorMessage({ response: { status: 429 } })).toContain("Too many attempts");
        expect(twoFactorErrorMessage({ response: { status: 503 } })).toContain("unavailable");
        expect(twoFactorErrorMessage({ response: { status: 409 } })).toContain("already active");
        expect(twoFactorErrorMessage({ response: { status: 400 } })).toBe("Invalid or expired code.");
        expect(twoFactorErrorMessage(new Error("network"))).toBe("Invalid or expired code.");
    });
});
