import { useEffect, useRef, useState } from "react";
import { PixiPetRuntime } from "./animation/PixiPetRuntime";
import { loadAnimationCatalog } from "./animation/loadAnimationCatalog";
import { loadAnimationRegistry } from "./animation/loadAnimationRegistry";
import { LocalBehaviorScheduler } from "./behavior/LocalBehaviorScheduler";
import { PetStateMachine } from "./behavior/PetStateMachine";
import { loadBehaviorConfig } from "./behavior/loadBehaviorConfig";
import type { PetDirection, PetState } from "./behavior/types";
import { loadCharacterConfig } from "./character/loadCharacterConfig";
import { loadRuntimeConfig } from "./character/loadRuntimeConfig";
import { TauriWindowService } from "./platform/TauriWindowService";
import "./App.css";

function App() {
  const stageRef = useRef<HTMLDivElement>(null);
  const [sizePercent, setSizePercent] = useState(100);
  const [petState, setPetState] = useState<PetState>("Idle");
  const [lastDirection, setLastDirection] = useState<PetDirection>("down");
  const [lastMicroActionId, setLastMicroActionId] = useState("");

  useEffect(() => {
    const stageElement = stageRef.current;
    if (!stageElement) {
      return;
    }

    let disposed = false;
    let windowService: TauriWindowService | null = null;
    let pixiRuntime: PixiPetRuntime | null = null;
    let stateMachine: PetStateMachine | null = null;
    let behaviorScheduler: LocalBehaviorScheduler | null = null;
    let removeAnimationCompleteListener: (() => void) | null = null;
    let removeDragMoveListener: (() => void) | null = null;
    let removeDragEndListener: (() => void) | null = null;
    let sizeConfig: Awaited<ReturnType<typeof loadBehaviorConfig>>["size"];
    let applySize: (percent: number) => Promise<void> = async () => undefined;

    const endDrag = () => {
      if (!windowService?.isDragging) {
        return;
      }
      void windowService.stopNativeDrag();
      windowService.endDrag();
      stateMachine?.endDrag();
    };

    const handleNativeDragEnd = () => {
      stateMachine?.endDrag();
    };

    const handlePointerDown = (event: PointerEvent) => {
      if (event.button !== 0 || !windowService || !stateMachine) {
        return;
      }
      event.preventDefault();
      windowService.beginDrag();
      stateMachine.beginDrag();
      void windowService.startNativeDrag().catch((error: unknown) => {
        console.error("Unable to start native window dragging", error);
        if (windowService?.isDragging) {
          windowService.endDrag();
          stateMachine?.endDrag();
        }
      });
    };

    const handlePointerEnter = () => {
      stateMachine?.hoverEnter();
    };

    const handleContextMenu = (event: MouseEvent) => {
      event.preventDefault();
      if (!windowService || !sizeConfig) {
        return;
      }
      void windowService.showPetMenu(sizeConfig, (percent) => {
        void applySize(percent);
      });
    };

    const initialize = async () => {
      const [character, catalog, animationRegistry, runtimeConfig, behaviorConfig] =
        await Promise.all([
          loadCharacterConfig(),
          loadAnimationCatalog(),
          loadAnimationRegistry(),
          loadRuntimeConfig(),
          loadBehaviorConfig(),
        ]);

      if (disposed) {
        return;
      }

      sizeConfig = behaviorConfig.size;
      windowService = new TauriWindowService();
      const initialPercent = windowService.readStoredSizePercent(
        behaviorConfig.size,
      );
      const initialSize = await windowService.applySizePercent(
        initialPercent,
        behaviorConfig.size,
        character.canvas.width,
        character.canvas.height,
      );
      await windowService.initialize();

      if (disposed) {
        windowService.dispose();
        return;
      }

      setSizePercent(initialSize.percent);
      pixiRuntime = await PixiPetRuntime.create(
        stageElement,
        character,
        catalog,
        runtimeConfig,
        initialSize.scale,
      );

      if (disposed) {
        pixiRuntime.dispose();
        windowService.dispose();
        return;
      }

      stateMachine = new PetStateMachine(
        behaviorConfig,
        {
          playAnimation: (animationId) => pixiRuntime?.play(animationId),
          onStateChange: setPetState,
          onDirectionChange: setLastDirection,
          onMicroAction: setLastMicroActionId,
        },
        animationRegistry,
      );
      removeAnimationCompleteListener = pixiRuntime.onAnimationComplete(
        (animationId) => stateMachine?.handleAnimationComplete(animationId),
      );
      removeDragMoveListener = windowService.onDragMove((delta) => {
        stateMachine?.updateDrag(delta.dx, delta.dy);
      });
      removeDragEndListener = windowService.onDragEnd(handleNativeDragEnd);

      applySize = async (percent) => {
        if (!windowService || !pixiRuntime) {
          return;
        }
        const size = await windowService.applySizePercent(
          percent,
          behaviorConfig.size,
          character.canvas.width,
          character.canvas.height,
        );
        if (disposed) {
          return;
        }
        pixiRuntime.resize(size.width, size.height, size.scale);
        setSizePercent(size.percent);
      };

      behaviorScheduler = new LocalBehaviorScheduler(
        behaviorConfig.microActions,
        () => stateMachine?.tryIdleShortAction(),
      );

      stageElement.addEventListener("pointerdown", handlePointerDown);
      stageElement.addEventListener("pointerenter", handlePointerEnter);
      stageElement.addEventListener("contextmenu", handleContextMenu);
      window.addEventListener("pointerup", endDrag);
      window.addEventListener("pointercancel", endDrag);

      stateMachine.start();
      behaviorScheduler.start();
    };

    void initialize().catch((error: unknown) => {
      console.error("Unable to initialize desktop pet", error);
    });

    return () => {
      disposed = true;
      stageElement.removeEventListener("pointerdown", handlePointerDown);
      stageElement.removeEventListener("pointerenter", handlePointerEnter);
      stageElement.removeEventListener("contextmenu", handleContextMenu);
      window.removeEventListener("pointerup", endDrag);
      window.removeEventListener("pointercancel", endDrag);
      behaviorScheduler?.stop();
      removeAnimationCompleteListener?.();
      removeDragMoveListener?.();
      removeDragEndListener?.();
      windowService?.dispose();
      pixiRuntime?.dispose();
    };
  }, []);

  return (
    <main
      className="pet-window"
      data-pet-state={petState}
      data-last-direction={lastDirection}
      data-last-micro-action={lastMicroActionId}
      data-size-percent={sizePercent}
    >
      <div ref={stageRef} className="pet-stage" aria-label="desktop pet" />
    </main>
  );
}

export default App;
