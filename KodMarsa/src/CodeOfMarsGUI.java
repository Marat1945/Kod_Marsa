import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.event.DocumentEvent;
import java.awt.*;
import java.awt.datatransfer.*;
import java.awt.image.BufferedImage;
import java.awt.event.*;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

public class CodeOfMarsGUI extends JFrame {
    private JTextArea inputArea, base32Area, morseArea;
    private JTextField phraseField, hexField;
    private JComboBox<String> keyComboBox;
    private JPanel phrasePanel, hexPanel;
    private List<String> predefinedKeys;

    public CodeOfMarsGUI() {
        setTitle("Код Марса");
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setSize(820, 750);
        setLocationRelativeTo(null);
        setLayout(new BorderLayout());

        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new EmptyBorder(10, 10, 10, 10));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);

        // 🔑 Ключ-фраза
        phrasePanel = new JPanel(new BorderLayout());
        phrasePanel.add(new JLabel("Ключ-фраза (SHA-256):"), BorderLayout.WEST);
        phraseField = new JTextField();
        phrasePanel.add(phraseField, BorderLayout.CENTER);
        gbc.gridx = 0; gbc.gridy = 0; gbc.gridwidth = 2;
        panel.add(phrasePanel, gbc);

        phraseField.getDocument().addDocumentListener((SimpleListener) e -> {
            try {
                String phrase = phraseField.getText().trim();
                if (!phrase.isEmpty()) {
                    byte[] key = CryptoUtil.sha256FromPhrase(phrase);
                    hexField.setText(CryptoUtil.bytesToHex(key));
                }
            } catch (Exception ignored) {}
        });

        // 🔑 HEX
        hexPanel = new JPanel(new BorderLayout());
        hexPanel.add(new JLabel("HEX-ключ (256 бит):"), BorderLayout.WEST);
        hexField = new JTextField();
        hexPanel.add(hexField, BorderLayout.CENTER);
        gbc.gridy++;
        panel.add(hexPanel, gbc);

        // 🔑 Список ключей
        gbc.gridy++; gbc.gridwidth = 1;
        panel.add(new JLabel("Выбрать ключ:"), gbc);
        keyComboBox = new JComboBox<>();
        keyComboBox.addItem("Вручную");
        keyComboBox.addItem("Универсальный");
        for (int i = 1; i <= 31; i++) keyComboBox.addItem("Ключ " + i);
        gbc.gridx = 1;
        panel.add(keyComboBox, gbc);
        keyComboBox.addActionListener(e -> toggleKeyFields());

        // 📝 Ввод текста
        gbc.gridx = 0; gbc.gridy++; gbc.gridwidth = 2;
        panel.add(new JLabel("Вводимый текст:"), gbc);
        inputArea = new JTextArea(5, 60);
        addContextMenu(inputArea);
        inputArea.getDocument().addDocumentListener((SimpleListener) e -> clearOutputs());
        inputArea.addKeyListener(new KeyAdapter() {
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER && !e.isShiftDown()) {
                    e.consume();
                    encryptAction(null);
                }
            }
        });
        gbc.gridy++;
        panel.add(new JScrollPane(inputArea), gbc);

        // 📦 Base32
        gbc.gridy++;
        panel.add(new JLabel("Результат (Base32):"), gbc);
        base32Area = new JTextArea(4, 60);
        addContextMenu(base32Area);
        base32Area.addKeyListener(new KeyAdapter() {
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER && !e.isShiftDown()) {
                    e.consume();
                    decryptAction(null);
                }
            }
        });
        gbc.gridy++;
        panel.add(new JScrollPane(base32Area), gbc);

        // 📡 Морзе
        gbc.gridy++;
        panel.add(new JLabel("Азбука Морзе:"), gbc);
        morseArea = new JTextArea(4, 60);
        morseArea.setEditable(false);
        addContextMenu(morseArea);
        gbc.gridy++;
        panel.add(new JScrollPane(morseArea), gbc);

        // 🔘 Кнопки
        JPanel buttonPanel = new JPanel();
        JButton encryptButton = new JButton("🔒 Шифровать");
        JButton decryptButton = new JButton("🔓 Дешифровать");
        JButton qrButton = new JButton("📷 QR-код");
        JButton loadQRButton = new JButton("📥 Загрузить QR");

        encryptButton.addActionListener(this::encryptAction);
        decryptButton.addActionListener(this::decryptAction);

        qrButton.addActionListener(e -> {
            try {
                String base32 = base32Area.getText().trim();
                if (base32.isEmpty()) return;
                BufferedImage bufferedImage = QRUtil.generateQR(base32);
                ImageIcon icon = new ImageIcon(bufferedImage);
                JLabel label = new JLabel(icon);
                JPopupMenu menu = new JPopupMenu();
                JMenuItem copy = new JMenuItem("Скопировать QR-код");
                copy.addActionListener(ev -> {
                    Clipboard clipboard = Toolkit.getDefaultToolkit().getSystemClipboard();
                    clipboard.setContents(new ImageSelection(icon.getImage()), null);
                });
                menu.add(copy);
                label.setComponentPopupMenu(menu);
                JOptionPane.showMessageDialog(this, label, "QR-код", JOptionPane.PLAIN_MESSAGE);
                QRUtil.saveQR(base32, "qr_output.png");
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(this, "Ошибка QR: " + ex.getMessage());
            }
        });

        loadQRButton.addActionListener(e -> {
            JFileChooser fileChooser = new JFileChooser();
            int result = fileChooser.showOpenDialog(this);
            if (result == JFileChooser.APPROVE_OPTION) {
                File file = fileChooser.getSelectedFile();
                try {
                    String qrText = QRUtil.decodeQR(file);
                    base32Area.setText(qrText);
                    decryptAction(null);
                } catch (Exception ex) {
                    JOptionPane.showMessageDialog(this, "Ошибка чтения QR: " + ex.getMessage());
                }
            }
        });

        buttonPanel.add(encryptButton);
        buttonPanel.add(decryptButton);
        buttonPanel.add(qrButton);
        buttonPanel.add(loadQRButton);
        gbc.gridy++;
        panel.add(buttonPanel, gbc);

        add(panel, BorderLayout.CENTER);
        loadPredefinedKeys();
        toggleKeyFields();
        setVisible(true);
    }

    private void toggleKeyFields() {
        boolean manual = keyComboBox.getSelectedIndex() == 0;
        phrasePanel.setVisible(manual);
        hexPanel.setVisible(manual);
    }

    private void encryptAction(ActionEvent e) {
        try {
            String input = inputArea.getText();
            if (input.isEmpty()) return;
            byte[] key = resolveKey();
            byte[] encrypted = CryptoUtil.encrypt(input, key);
            String base32 = Base32Util.encode(encrypted);
            if (!base32.matches("^[A-Z2-7]+$")) {
                JOptionPane.showMessageDialog(this, "❗ Base32 содержит символы, не поддерживаемые азбукой Морзе");
            }
            String morse = MorseUtil.toMorse(base32);
            base32Area.setText(base32);
            morseArea.setText(morse);
        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, "Ошибка шифрования: " + ex.getMessage());
        }
    }

    private void decryptAction(ActionEvent e) {
        try {
            String base32 = base32Area.getText().trim();
            if (base32.isEmpty()) return;
            byte[] key = resolveKey();
            byte[] decoded = Base32Util.decode(base32);
            String result = CryptoUtil.decrypt(decoded, key);
            inputArea.setText(result);
        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, "Ошибка дешифровки: " + ex.getMessage());
        }
    }

    private byte[] resolveKey() throws Exception {
        int index = keyComboBox.getSelectedIndex();
        if (index == 0) {
            String phrase = phraseField.getText().trim();
            String hex = hexField.getText().trim();
            if (!phrase.isEmpty()) return CryptoUtil.sha256FromPhrase(phrase);
            else if (!hex.isEmpty()) return CryptoUtil.hexToBytes(hex);
            else throw new Exception("Введите ключ-фразу или HEX-ключ");
        } else {
            return CryptoUtil.hexToBytes(predefinedKeys.get(index - 1));
        }
    }

    private void loadPredefinedKeys() {
        try {
            predefinedKeys = Files.readAllLines(Paths.get("keys.txt"));
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Не удалось загрузить keys.txt");
            predefinedKeys = List.of(new String[32]);
        }
    }

    private void clearOutputs() {
        base32Area.setText("");
        morseArea.setText("");
    }

    private void addContextMenu(JTextArea area) {
        JPopupMenu menu = new JPopupMenu();
        JMenuItem copy = new JMenuItem("Копировать");
        JMenuItem paste = new JMenuItem("Вставить");
        JMenuItem clear = new JMenuItem("Очистить");

        copy.addActionListener(e -> area.copy());
        paste.addActionListener(e -> area.paste());
        clear.addActionListener(e -> area.setText(""));

        menu.add(copy);
        menu.add(paste);
        menu.add(clear);

        area.setComponentPopupMenu(menu);
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(CodeOfMarsGUI::new);
    }
}

@FunctionalInterface
interface SimpleListener extends javax.swing.event.DocumentListener {
    void update(DocumentEvent e);
    @Override default void insertUpdate(DocumentEvent e) { update(e); }
    @Override default void removeUpdate(DocumentEvent e) { update(e); }
    @Override default void changedUpdate(DocumentEvent e) { update(e); }
}

class ImageSelection implements Transferable {
    private final Image image;
    public ImageSelection(Image image) { this.image = image; }

    public DataFlavor[] getTransferDataFlavors() {
        return new DataFlavor[]{DataFlavor.imageFlavor};
    }

    public boolean isDataFlavorSupported(DataFlavor flavor) {
        return DataFlavor.imageFlavor.equals(flavor);
    }

    public Object getTransferData(DataFlavor flavor) {
        if (isDataFlavorSupported(flavor)) return image;
        return null;
    }
}
