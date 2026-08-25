import type { CadreDatabase } from "./client";
import { getDatabase } from "./client";
import { workspaces } from "./schema";

export const INITIAL_WORKSPACES = [
  {
    slug: "cadre-governance",
    name: "CADRE Governance",
    description: "Parent-platform governance and doctrine operations."
  },
  {
    slug: "vessel",
    name: "VESSEL",
    description: "Flagship workspace reserved for future VESSEL services."
  },
  {
    slug: "chozen-voyage",
    name: "CHOZEN Voyage",
    description: "CHOZEN Voyage projects and operations."
  },
  {
    slug: "majestic-lifestyle",
    name: "Majestic Lifestyle",
    description: "Majestic Lifestyle projects and operations."
  },
  {
    slug: "majic-by-majestic",
    name: "Majic by Majestic",
    description: "Majic by Majestic projects and operations."
  },
  {
    slug: "breathe-deepr",
    name: "Breathe DEEPR",
    description: "Breathe DEEPR projects and operations."
  },
  {
    slug: "sirrah-publishing",
    name: "Sirrah Publishing",
    description: "Sirrah Publishing projects and operations."
  },
  {
    slug: "incubator",
    name: "Incubator",
    description: "Governed workspace for future initiatives."
  }
] as const;

export async function seedWorkspaces(database?: CadreDatabase): Promise<number> {
  const db = database ?? (await getDatabase());
  const inserted = await db
    .insert(workspaces)
    .values(INITIAL_WORKSPACES.map((workspace) => ({ ...workspace })))
    .onConflictDoNothing({ target: workspaces.slug })
    .returning();

  return inserted.length;
}
