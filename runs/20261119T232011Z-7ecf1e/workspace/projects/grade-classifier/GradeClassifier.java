package examples;

public class GradeClassifier {
    public static String classify(int score) {
        if (score < 0 || score > 100) {
            throw new IllegalArgumentException("score out of range: " + score);
        }
        if (score >= 90) return "A";
        if (score >= 80) return "B";
        if (score >= 70) return "C";
        if (score >= 60) return "D";
        return "F";
    }
}
