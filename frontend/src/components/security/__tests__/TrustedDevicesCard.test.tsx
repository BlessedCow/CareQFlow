import {
    fireEvent,
    render,
    screen,
    waitFor,
  } from "@testing-library/react";
  import { beforeEach, describe, expect, it, vi } from "vitest";
  
  import { revokeTrustedDevices } from "../../../api/security";
  import { TrustedDevicesCard } from "../TrustedDevicesCard";
  
  vi.mock("../../../api/security", () => ({
    revokeTrustedDevices: vi.fn(),
  }));
  
  const mockedRevokeTrustedDevices = vi.mocked(revokeTrustedDevices);
  
  describe("TrustedDevicesCard", () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });
  
    it("revokes remembered devices", async () => {
      mockedRevokeTrustedDevices.mockResolvedValue({
        trusted_devices_revoked: 2,
      });
  
      render(<TrustedDevicesCard darkMode={false} />);
  
      fireEvent.click(
        screen.getByRole("button", {
          name: "Revoke remembered devices",
        })
      );
  
      await waitFor(() => {
        expect(mockedRevokeTrustedDevices).toHaveBeenCalledTimes(1);
      });
  
      expect(
        screen.getByText("2 remembered devices were revoked.")
      ).toBeInTheDocument();
    });
  
    it("reports when no remembered devices exist", async () => {
      mockedRevokeTrustedDevices.mockResolvedValue({
        trusted_devices_revoked: 0,
      });
  
      render(<TrustedDevicesCard darkMode={false} />);
  
      fireEvent.click(
        screen.getByRole("button", {
          name: "Revoke remembered devices",
        })
      );
  
      expect(
        await screen.findByText("0 remembered devices were revoked.")
      ).toBeInTheDocument();
    });
  
    it("shows revocation errors", async () => {
      mockedRevokeTrustedDevices.mockRejectedValue(
        new Error("Unable to revoke remembered devices.")
      );
  
      render(<TrustedDevicesCard darkMode={false} />);
  
      fireEvent.click(
        screen.getByRole("button", {
          name: "Revoke remembered devices",
        })
      );
  
      expect(
        await screen.findByRole("alert")
      ).toHaveTextContent("Unable to revoke remembered devices.");
    });
  });