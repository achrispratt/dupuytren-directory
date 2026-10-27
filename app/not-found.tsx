import Link from "next/link";

export default function NotFound() {
  return (
    <div className="panel empty" style={{ margin: "40px 0" }}>
      <h1>Not found</h1>
      <p>
        That listing doesn&apos;t exist, or it was merged into another one. <Link href="/">Search the directory</Link>.
      </p>
    </div>
  );
}
