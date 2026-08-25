import { randomBytes, scrypt as nodeScrypt, timingSafeEqual } from "node:crypto";

const SCRYPT_N = 2 ** 16;
const SCRYPT_R = 8;
const SCRYPT_P = 2;
const SCRYPT_KEY_LENGTH = 32;
const SCRYPT_MAX_MEMORY = 128 * 1024 * 1024;
const SALT_LENGTH = 16;

export const MINIMUM_PASSWORD_LENGTH = 14;
export const MAXIMUM_PASSWORD_BYTES = 1024;

function scrypt(
  password: string,
  salt: Buffer,
  keyLength: number,
  n: number,
  r: number,
  p: number
): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    nodeScrypt(
      password,
      salt,
      keyLength,
      { N: n, r, p, maxmem: SCRYPT_MAX_MEMORY },
      (error, derivedKey) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(derivedKey);
      }
    );
  });
}

export function assertPasswordPolicy(password: string): void {
  if (password.length < MINIMUM_PASSWORD_LENGTH) {
    throw new Error(`Password must contain at least ${MINIMUM_PASSWORD_LENGTH} characters.`);
  }
  if (Buffer.byteLength(password, "utf8") > MAXIMUM_PASSWORD_BYTES) {
    throw new Error(`Password must not exceed ${MAXIMUM_PASSWORD_BYTES} UTF-8 bytes.`);
  }
  if (/\u0000/.test(password)) {
    throw new Error("Password must not contain a null character.");
  }
}

export async function hashPassword(password: string): Promise<string> {
  assertPasswordPolicy(password);
  const salt = randomBytes(SALT_LENGTH);
  const derivedKey = await scrypt(password, salt, SCRYPT_KEY_LENGTH, SCRYPT_N, SCRYPT_R, SCRYPT_P);
  return [
    "scrypt",
    SCRYPT_N.toString(),
    SCRYPT_R.toString(),
    SCRYPT_P.toString(),
    salt.toString("base64url"),
    derivedKey.toString("base64url")
  ].join("$");
}

export async function verifyPassword(password: string, encodedHash: string): Promise<boolean> {
  const parts = encodedHash.split("$");
  if (parts.length !== 6 || parts[0] !== "scrypt") {
    return false;
  }

  const n = Number(parts[1]);
  const r = Number(parts[2]);
  const p = Number(parts[3]);
  if (
    !Number.isSafeInteger(n) ||
    !Number.isSafeInteger(r) ||
    !Number.isSafeInteger(p) ||
    n < 2 ** 14 ||
    n > 2 ** 18 ||
    (n & (n - 1)) !== 0 ||
    r < 1 ||
    r > 16 ||
    p < 1 ||
    p > 10
  ) {
    return false;
  }

  let salt: Buffer;
  let expected: Buffer;
  try {
    salt = Buffer.from(parts[4], "base64url");
    expected = Buffer.from(parts[5], "base64url");
  } catch {
    return false;
  }

  if (salt.length < 16 || expected.length !== SCRYPT_KEY_LENGTH) {
    return false;
  }

  try {
    const actual = await scrypt(password, salt, expected.length, n, r, p);
    return timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}
