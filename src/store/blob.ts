/**
 * Blob storage for bundle files. R2 in production (unbounded, no egress
 * fees), in-memory for tests. Keys are content-addressed under the build's
 * cid, so a stored file can never be swapped without changing the id.
 */

export interface BlobStore {
  put(key: string, bytes: Uint8Array, contentType: string): Promise<void>;
  get(key: string): Promise<{ bytes: Uint8Array; contentType: string } | null>;
  has(key: string): Promise<boolean>;
}

export class MemoryBlobStore implements BlobStore {
  private blobs = new Map<string, { bytes: Uint8Array; contentType: string }>();
  async put(key: string, bytes: Uint8Array, contentType: string): Promise<void> {
    this.blobs.set(key, { bytes: bytes.slice(), contentType });
  }
  async get(key: string): Promise<{ bytes: Uint8Array; contentType: string } | null> {
    const b = this.blobs.get(key);
    return b ? { bytes: b.bytes.slice(), contentType: b.contentType } : null;
  }
  async has(key: string): Promise<boolean> {
    return this.blobs.has(key);
  }
}

/** Thin R2 adapter; bound in the Workers. */
export class R2BlobStore implements BlobStore {
  constructor(private bucket: R2Bucket) {}
  async put(key: string, bytes: Uint8Array, contentType: string): Promise<void> {
    await this.bucket.put(key, bytes as unknown as ArrayBuffer, {
      httpMetadata: { contentType },
    });
  }
  async get(key: string): Promise<{ bytes: Uint8Array; contentType: string } | null> {
    const obj = await this.bucket.get(key);
    if (!obj) return null;
    return {
      bytes: new Uint8Array(await obj.arrayBuffer()),
      contentType: obj.httpMetadata?.contentType ?? "application/octet-stream",
    };
  }
  async has(key: string): Promise<boolean> {
    return (await this.bucket.head(key)) !== null;
  }
}

export const bundleKey = (cid: string, path: string): string =>
  `bundles/${cid.replace(/^ecd:cid:/, "")}/${path}`;
