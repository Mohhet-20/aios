import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoginForm } from "@/app/login/login-form";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }) }));

describe("LoginForm", () => {
  it("offers no guest session, and shows no credentials, by default", () => {
    const { container } = render(<LoginForm next="/dashboard" guest={false} />);
    expect(screen.queryByRole("button", { name: "Explore the live demo" })).toBeNull();
    expect(container.textContent).not.toMatch(/Northwind-Demo|demo@aios/);
  });

  it("offers the guest session on a hosted demo, still without any credentials", () => {
    const { container } = render(<LoginForm next="/dashboard" guest />);
    expect(screen.getByRole("button", { name: "Explore the live demo" })).not.toBeNull();
    expect(container.textContent).not.toMatch(/password\s*[:/]|Northwind-Demo|demo@aios/i);
  });
});
