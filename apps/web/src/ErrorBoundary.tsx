import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Stitchord UI crashed", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="fatal">
          <h1>界面遇到错误</h1>
          <p>{this.state.error.message}</p>
          <p className="hint">
            当前工程仍保存在浏览器本地（localStorage）。刷新后通常可恢复；
            若反复出现，请先“保存工程”再刷新。
          </p>
          <button type="button" onClick={() => window.location.reload()}>
            刷新页面
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
