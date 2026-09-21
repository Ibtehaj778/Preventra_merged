import { Component } from "react";

export class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card p-6 text-center">
          <div className="text-sm font-semibold text-red-600 mb-1">
            Failed to load this section
          </div>
          <div className="text-xs text-gray-400 mb-3">
            {this.state.error.message}
          </div>
          <button
            onClick={() => this.setState({ error: null })}
            className="text-xs font-medium px-3 py-1.5 rounded-lg"
            style={{ background: "#EBF4FF", color: "var(--color-primary)" }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
