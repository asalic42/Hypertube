// Input lengths the movies service accepts (its serializers reject anything
// longer), so the fields stop the user at the same point instead of failing on
// submit. Keep them in step with movies_app/serializers.py.
export const SEARCH_MAX_LENGTH = 100;
export const COMMENT_MAX_LENGTH = 2000;
