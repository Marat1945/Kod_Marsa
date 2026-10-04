import java.util.HashMap;
import java.util.Map;

public class MorseUtil {
    private static final Map<Character, String> morseMap = new HashMap<>();
    static {
        morseMap.put('A', ".-");    morseMap.put('B', "-...");
        morseMap.put('C', "-.-.");  morseMap.put('D', "-..");
        morseMap.put('E', ".");     morseMap.put('F', "..-.");
        morseMap.put('G', "--.");   morseMap.put('H', "....");
        morseMap.put('I', "..");    morseMap.put('J', ".---");
        morseMap.put('K', "-.-");   morseMap.put('L', ".-..");
        morseMap.put('M', "--");    morseMap.put('N', "-.");
        morseMap.put('O', "---");   morseMap.put('P', ".--.");
        morseMap.put('Q', "--.-");  morseMap.put('R', ".-.");
        morseMap.put('S', "...");   morseMap.put('T', "-");
        morseMap.put('U', "..-");   morseMap.put('V', "...-");
        morseMap.put('W', ".--");   morseMap.put('X', "-..-");
        morseMap.put('Y', "-.--");  morseMap.put('Z', "--..");
        morseMap.put('0', "-----"); morseMap.put('1', ".----");
        morseMap.put('2', "..---"); morseMap.put('3', "...--");
        morseMap.put('4', "....-"); morseMap.put('5', ".....");
        morseMap.put('6', "-...."); morseMap.put('7', "--...");
        morseMap.put('8', "---.."); morseMap.put('9', "----.");
        morseMap.put('=', "-...-");
    }

    public static String toMorse(String input) {
        StringBuilder result = new StringBuilder();
        for (char ch : input.toUpperCase().toCharArray()) {
            if (morseMap.containsKey(ch)) {
                result.append(morseMap.get(ch)).append(" ");
            } else {
                result.append("? ");
            }
        }
        return result.toString().trim();
    }
}
