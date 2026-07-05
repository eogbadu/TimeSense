import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-semibold">TimeSense</h1>
      <p className="text-neutral-500">
        Don&apos;t make managing your day another job.
      </p>
      <Link
        href="/admin"
        className="rounded-full bg-neutral-900 px-5 py-2 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
      >
        Admin Dashboard
      </Link>
    </main>
  );
}
