import java.util.Arrays;

public class Base32Util {
    private static final char[] BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".toCharArray();
    private static final int[] BASE32_LOOKUP = new int[128];
    static {
        Arrays.fill(BASE32_LOOKUP, -1);
        for (int i = 0; i < BASE32_ALPHABET.length; i++) {
            BASE32_LOOKUP[BASE32_ALPHABET[i]] = i;
        }
    }

    public static String encode(byte[] data) {
        StringBuilder sb = new StringBuilder();
        int buffer = 0;
        int bitsLeft = 0;

        for (byte b : data) {
            buffer <<= 8;
            buffer |= b & 0xFF;
            bitsLeft += 8;

            while (bitsLeft >= 5) {
                sb.append(BASE32_ALPHABET[(buffer >> (bitsLeft - 5)) & 0x1F]);
                bitsLeft -= 5;
            }
        }

        if (bitsLeft > 0) {
            buffer <<= (5 - bitsLeft);
            sb.append(BASE32_ALPHABET[buffer & 0x1F]);
        }

        return sb.toString();
    }

    public static byte[] decode(String base32) throws IllegalArgumentException {
        base32 = base32.toUpperCase().replaceAll("[=\\s]", "");
        int buffer = 0;
        int bitsLeft = 0;
        int count = 0;
        byte[] result = new byte[base32.length() * 5 / 8];

        for (char c : base32.toCharArray()) {
            if (c >= BASE32_LOOKUP.length || BASE32_LOOKUP[c] == -1)
                throw new IllegalArgumentException("Недопустимый символ Base32: " + c);

            buffer <<= 5;
            buffer |= BASE32_LOOKUP[c];
            bitsLeft += 5;

            if (bitsLeft >= 8) {
                result[count++] = (byte) ((buffer >> (bitsLeft - 8)) & 0xFF);
                bitsLeft -= 8;
            }
        }

        return Arrays.copyOf(result, count);
    }
}
