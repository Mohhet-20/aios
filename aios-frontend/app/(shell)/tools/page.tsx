import { redirect } from "next/navigation";

/** Section root (breadcrumbs link here): send it to the section's main page. */
export default function Page() {
  redirect("/tools/plugins");
}
