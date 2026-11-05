export function prettyDate(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function prettyTime(value) {
  if (!value) return "";
  const [hour, minute] = value.split(":");
  const date = new Date();
  date.setHours(Number(hour), Number(minute), 0, 0);
  return date.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}

export function whenLabel(slot) {
  if (!slot) return "No open slot";
  return `${prettyDate(slot.date)} · ${prettyTime(slot.start_time)}`;
}

export function ratingLabel(avg, count) {
  if (!count) return "No ratings yet";
  const rounded = Math.round(Number(avg));
  const stars = "★★★★★".slice(0, rounded) + "☆☆☆☆☆".slice(0, 5 - rounded);
  return `${stars}  ${Number(avg).toFixed(1)} · ${count} rating${count === 1 ? "" : "s"}`;
}

export function waitLabel(minutes) {
  if (minutes === null || minutes === undefined) return "Picked up";
  if (minutes < 60) return `${minutes} min waiting`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h ${minutes % 60} min waiting`;
}

export function homeFor(user) {
  if (!user) return "/";
  if (user.role === "doctor") return "/doctor";
  if (user.role === "admin") return "/admin";
  return "/patient";
}
