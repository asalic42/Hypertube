import { useContext } from "react";
import { ThemeContext } from "@/lib/themeContext";

export function useTheme() {
  return useContext(ThemeContext);
}
