import { splitJobDescription } from "@/lib/jobDescription";

/**
 * A posting's own words, with its sections and lists set out.
 *
 * Runs of list items are gathered into one list so the markup says "list"
 * rather than leaving a reader to infer it from the bullets.
 */
export function JobDescription({ description }: { description: string }) {
  const blocks = splitJobDescription(description);

  if (blocks.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        This posting did not carry a description.
      </p>
    );
  }

  const rendered: React.ReactNode[] = [];
  let bullets: string[] = [];

  const flushBullets = () => {
    if (bullets.length === 0) {
      return;
    }

    rendered.push(
      <ul
        key={`list-${rendered.length}`}
        className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-text"
      >
        {bullets.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>,
    );

    bullets = [];
  };

  for (const block of blocks) {
    if (block.kind === "bullet") {
      bullets.push(block.text);
      continue;
    }

    flushBullets();

    rendered.push(
      block.kind === "heading" ? (
        <h4
          key={`heading-${rendered.length}`}
          className="mt-5 text-sm font-semibold text-text first:mt-0"
        >
          {block.text}
        </h4>
      ) : (
        <p
          key={`paragraph-${rendered.length}`}
          className="mt-2 text-sm leading-relaxed text-text"
        >
          {block.text}
        </p>
      ),
    );
  }

  flushBullets();

  return <div className="max-w-[70ch]">{rendered}</div>;
}
