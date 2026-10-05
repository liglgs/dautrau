import { openDB } from "idb";
import type { Store } from "../types";
import { seed } from "./seed";
const db = () =>
  openDB("vmec03-demo-v1", 1, {
    upgrade(database) {
      database.createObjectStore("state");
    },
  });
export async function readStore(): Promise<Store> {
  const database = await db();
  const tx = database.transaction("state", "readwrite");
  let state = (await tx.store.get("demo")) as Store | undefined;
  if (!state) {
    state = seed();
    await tx.store.put(state, "demo");
  }
  await tx.done;
  return state;
}
export async function mutate<T>(fn: (state: Store) => T): Promise<T> {
  const database = await db();
  const tx = database.transaction("state", "readwrite");
  try {
    const state = ((await tx.store.get("demo")) as Store | undefined) ?? seed();
    const result = fn(state);
    await tx.store.put(state, "demo");
    await tx.done;
    return result;
  } catch (error) {
    tx.abort();
    await tx.done.catch(() => {});
    throw error;
  }
}
