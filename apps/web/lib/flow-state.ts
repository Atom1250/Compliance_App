export type StepState = "idle" | "validating" | "submitting" | "success" | "error";

const TRANSITIONS: Record<StepState, StepState[]> = {
  idle: ["validating", "submitting", "error"],
  validating: ["submitting", "error"],
  submitting: ["success", "error"],
  success: ["idle", "submitting"],
  error: ["idle", "validating", "submitting"]
};

export function canTransition(from: StepState, to: StepState): boolean {
  return TRANSITIONS[from].includes(to);
}

export function transitionOrStay(current: StepState, target: StepState): StepState {
  return canTransition(current, target) ? target : current;
}

export function stateLabel(state: StepState): string {
  switch (state) {
    case "idle":
      return "Idle";
    case "validating":
      return "Validating input...";
    case "submitting":
      return "Submitting...";
    case "success":
      return "Completed";
    case "error":
      return "Failed";
    default:
      return "Idle";
  }
}
