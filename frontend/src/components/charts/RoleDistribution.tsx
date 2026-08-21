"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  RoleSkillsPanel,
  type RoleGroup,
} from "@/components/charts/RoleSkillsPanel";
import { layoutTreemap } from "@/components/charts/RoleTreemap";
import { TreemapTile } from "@/components/charts/TreemapTile";

export interface RoleShare {
  label: string;
  value: number;
  share: number;
}

function BackIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M16 10H4M9 5l-5 5 5 5" />
    </svg>
  );
}

/**
 * The role categories, and whichever one has been opened.
 *
 * The treemap is the picker: its tiles are already sized by how many postings
 * sit in each role, so choosing from them says something a list of names
 * cannot. Nothing is open to begin with, because the spread is the question
 * this view answers first.
 */
export function RoleDistribution({
  rows,
  roles,
  datasetName,
  header,
}: {
  rows: RoleShare[];
  roles: RoleGroup[];
  datasetName: string;
  /**
   * The page's own heading, handed in rather than rendered above this, so a
   * role opened on a narrow screen can take the whole page the way a job
   * posting does.
   */
  header: ReactNode;
}) {
  const skillsByRole = new Map(roles.map((role) => [role.roleCategory, role]));

  const [openRole, setOpenRole] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!openRole || !panelRef.current) {
      return;
    }

    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches
      ? "auto"
      : "smooth";

    /*
     * Below lg the opened role is the whole page, so it starts at the top of
     * it. Scrolling the panel into view instead puts its own top under the
     * bar that stays fixed above it, which reads as opening part way down.
     */
    if (!window.matchMedia("(min-width: 64rem)").matches) {
      window.scrollTo({ top: 0, behavior });
      return;
    }

    panelRef.current.scrollIntoView({ behavior, block: "start" });
  }, [openRole]);

  const tiles = layoutTreemap(rows);
  const shareOf = new Map(rows.map((row) => [row.label, row.share]));
  const selected = openRole ? skillsByRole.get(openRole) : undefined;

  return (
    <>
      <div className={selected ? "hidden lg:block" : ""}>{header}</div>

      {/* Card chrome from lg up. With a role open on a narrow screen this is
          not a card at all: it bleeds past the page padding and the panel
          reads as the page, the way an opened job posting does. */}
      <section
        // Outside the ternary so opening a role does not restart it: the
        // entrance belongs to arriving on the subtab, and the panel that
        // opens has an entrance of its own.
        className={`animate-section-in ${
          selected
            ? "-mx-5 -mb-8 -mt-8 bg-surface pb-8 sm:-mx-8 lg:mx-0 lg:mb-0 lg:mt-0 lg:pb-0 lg:rounded-xl lg:border lg:border-border lg:shadow-[0_1px_2px_rgba(16,21,31,0.04)]"
            : "rounded-xl border border-border bg-surface shadow-[0_1px_2px_rgba(16,21,31,0.04)]"
        }`}
        style={{ animationDelay: "60ms" }}
      >
        <div className={`p-4 sm:p-5 ${selected ? "hidden lg:block" : ""}`}>
          <div className="relative h-[26rem] w-full sm:h-[32rem]">
            {tiles.map((tile) => {
              const share = shareOf.get(tile.label) ?? 0;
              // A category with no skills breakdown has nothing to open, so
              // its tile stays a tile rather than pretending to be a choice.
              const hasSkills = skillsByRole.has(tile.label);

              return (
                <div
                  key={tile.label}
                  className="absolute p-1"
                  style={{
                    left: `${tile.x}%`,
                    top: `${tile.y}%`,
                    width: `${tile.width}%`,
                    height: `${tile.height}%`,
                  }}
                >
                  <TreemapTile
                    label={tile.label}
                    value={tile.value}
                    share={share}
                    top={tile.y}
                    step={tile.step}
                    // Height is what limits stacked content, not area: a wide,
                    // short tile has plenty of area and no room.
                    showIcon={tile.height >= 30}
                    showShare={tile.height >= 22}
                    onSelect={
                      hasSkills ? () => setOpenRole(tile.label) : undefined
                    }
                  />
                </div>
              );
            })}
          </div>
        </div>

        {selected ? (
          <div ref={panelRef} className="scroll-mt-6 lg:border-t lg:border-border">
            <Link
              href="#"
              onClick={(event) => {
                event.preventDefault();
                setOpenRole(null);
              }}
              className="flex items-center gap-2 px-5 pb-3 pt-5 text-sm font-medium text-text-muted transition-colors hover:text-text lg:hidden"
            >
              <BackIcon />
              Back to categories
            </Link>

            <RoleSkillsPanel
              role={selected}
              // The category is a filter of its own, so it arrives as one,
              // with the panel open so it is clear what narrowed the list.
              jobsHref={`/jobs?dataset=${encodeURIComponent(
                datasetName,
              )}&category=${encodeURIComponent(
                selected.roleCategory,
              )}&filters=open`}
            />
          </div>
        ) : null}
      </section>
    </>
  );
}
