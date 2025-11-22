export function clickOutside(node: HTMLElement, onOutside: () => void) {
  const handleClick = (event: MouseEvent) => {
    const target = event.target as Node;
    if (node && !node.contains(target) && !event.defaultPrevented) {
      onOutside();
    }
  };

  document.addEventListener("click", handleClick, true);

  return {
    destroy() {
      document.removeEventListener("click", handleClick, true);
    }
  };
}
