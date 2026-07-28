import { render, screen } from "@testing-library/react";

function TestComponent() {
  return <p>Frontend testing is configured.</p>;
}

describe("frontend test setup", () => {
  it("renders React components with DOM matchers", () => {
    render(<TestComponent />);

    expect(
      screen.getByText("Frontend testing is configured.")
    ).toBeInTheDocument();
  });
});
