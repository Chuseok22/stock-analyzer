"""
Example Spring Boot integration service.
This shows how to call the Python ML system from Spring Boot.
"""

# Java Spring Boot Service Example
"""
@Service
public class StockAnalysisService {
    
    private final String PYTHON_SCRIPT_PATH = "/path/to/stock-analyzer/run.sh";
    
    @Scheduled(cron = "0 0 18 * * MON-FRI") // 평일 오후 6시 실행
    public void generateDailyRecommendations() {
        try {
            // 전체 파이프라인 실행 (데이터 수집 + 추천 생성)
            String command = String.format(
                "bash %s pipeline --universe-id 1 --top-n 20", 
                PYTHON_SCRIPT_PATH
            );
            
            ProcessResult result = executeCommand(command);
            
            if (result.isSuccess()) {
                // 성공 시 결과 처리
                JsonNode recommendations = parseJsonResult(result.getOutput());
                processRecommendations(recommendations);
            } else {
                // 실패 시 에러 처리
                log.error("Python ML system failed: {}", result.getError());
            }
            
        } catch (Exception e) {
            log.error("Failed to execute stock analysis", e);
        }
    }
    
    @Scheduled(cron = "0 0 9 * * SAT") // 매주 토요일 오전 9시 모델 재학습
    public void weeklyModelRetraining() {
        try {
            String command = String.format(
                "bash %s train --universe-id 1 --retrain", 
                PYTHON_SCRIPT_PATH
            );
            
            ProcessResult result = executeCommand(command);
            
            if (result.isSuccess()) {
                log.info("Model retraining completed successfully");
            } else {
                log.error("Model retraining failed: {}", result.getError());
            }
            
        } catch (Exception e) {
            log.error("Failed to retrain model", e);
        }
    }
    
    @Scheduled(cron = "0 0 1 1 * *") // 매월 1일 오전 1시 유니버스 업데이트
    public void monthlyUniverseUpdate() {
        try {
            String command = String.format(
                "bash %s update-universe --region KR --top-n 200", 
                PYTHON_SCRIPT_PATH
            );
            
            ProcessResult result = executeCommand(command);
            
            if (result.isSuccess()) {
                JsonNode response = parseJsonResult(result.getOutput());
                Integer universeId = response.get("universe_id").asInt();
                
                // 새로운 유니버스 ID로 시스템 설정 업데이트
                updateUniverseId(universeId);
                
                log.info("Universe updated successfully. New Universe ID: {}", universeId);
            } else {
                log.error("Universe update failed: {}", result.getError());
            }
            
        } catch (Exception e) {
            log.error("Failed to update universe", e);
        }
    }
    
    public RecommendationAnalysis getPerformanceAnalysis(int days) {
        try {
            String command = String.format(
                "bash %s performance --days %d", 
                PYTHON_SCRIPT_PATH, days
            );
            
            ProcessResult result = executeCommand(command);
            
            if (result.isSuccess()) {
                JsonNode response = parseJsonResult(result.getOutput());
                return parsePerformanceMetrics(response);
            } else {
                throw new RuntimeException("Performance analysis failed: " + result.getError());
            }
            
        } catch (Exception e) {
            log.error("Failed to get performance analysis", e);
            throw new RuntimeException("Performance analysis failed", e);
        }
    }
    
    private ProcessResult executeCommand(String command) throws Exception {
        ProcessBuilder processBuilder = new ProcessBuilder("bash", "-c", command);
        processBuilder.directory(new File(PYTHON_SCRIPT_PATH).getParentFile());
        
        Process process = processBuilder.start();
        
        // 출력 읽기
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        String error = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
        
        int exitCode = process.waitFor();
        
        return new ProcessResult(exitCode == 0, output, error);
    }
    
    private JsonNode parseJsonResult(String output) throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        return mapper.readTree(output);
    }
    
    private void processRecommendations(JsonNode recommendations) {
        // 추천 결과를 데이터베이스에 저장하거나 알림 발송
        // Spring Boot의 Recommendation 엔티티와 연동
    }
    
    private void updateUniverseId(Integer universeId) {
        // 시스템 설정에 새로운 유니버스 ID 저장
    }
    
    private RecommendationAnalysis parsePerformanceMetrics(JsonNode response) {
        // JSON 응답을 RecommendationAnalysis 객체로 변환
        return new RecommendationAnalysis();
    }
    
    // 내부 클래스들
    private static class ProcessResult {
        private final boolean success;
        private final String output;
        private final String error;
        
        public ProcessResult(boolean success, String output, String error) {
            this.success = success;
            this.output = output;
            this.error = error;
        }
        
        // getters...
    }
}
"""

# Python 시스템 호출 예시들:

# 1. 일일 추천 생성
# bash run.sh pipeline --universe-id 1 --top-n 20

# 2. 주간 모델 재학습
# bash run.sh train --universe-id 1 --retrain

# 3. 월간 유니버스 업데이트
# bash run.sh update-universe --region KR --top-n 200

# 4. 성과 분석
# bash run.sh performance --days 30

# 5. 수동 데이터 수집
# bash run.sh collect --universe-id 1 --days 252
